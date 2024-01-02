import math

import requests
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh
from specklepy.objects.units import get_scale_factor_to_meters

from utils.utils_geometry import (
    create_flat_mesh,
    extrude_building,
    generate_points_inside_polygon,
    generate_tree,
    join_roads,
    road_buffer,
    rotate_pt,
    split_ways_by_intersection,
)
from utils.utils_other import (
    COLOR_BASE,
    clean_string,
    get_degrees_bbox_from_lat_lon_rad,
)
from utils.utils_pyproj import create_crs, reproject_to_crs


def get_base_plane(lat: float, lon: float, r: float, units: float) -> Base:
    """Get a square base plane."""
    scale_factor = get_scale_factor_to_meters(units)
    min_lat_lon, max_lat_lon = get_degrees_bbox_from_lat_lon_rad(lat, lon, r)
    projected_crs = create_crs(lat, lon)
    min_xy = reproject_to_crs(
        min_lat_lon[0], min_lat_lon[1], "EPSG:4326", projected_crs
    )
    max_xy = reproject_to_crs(
        max_lat_lon[0], max_lat_lon[1], "EPSG:4326", projected_crs
    )

    color = COLOR_BASE
    colors = [color, color, color, color]
    faces = [4, 0, 1, 2, 3]

    vertices = [
        min_xy[0] / scale_factor,
        min_xy[1] / scale_factor,
        0,
        max_xy[0] / scale_factor,
        min_xy[1] / scale_factor,
        0,
        max_xy[0] / scale_factor,
        max_xy[1] / scale_factor,
        0,
        min_xy[0] / scale_factor,
        max_xy[1] / scale_factor,
        0,
    ]

    obj = Mesh.create(faces=faces, vertices=vertices, colors=colors)
    obj.units = units

    base_obj = Base(
        units=units,
        displayValue=[obj],
    )

    return base_obj


def get_features_from_osm_server(
    keyword: str, min_lat_lon: tuple[float], max_lat_lon: tuple[float]
) -> list[dict]:
    """Get OSM features via Overpass API."""
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""[out:json];
    (node["{keyword}"]({min_lat_lon[0]},{min_lat_lon[1]},{max_lat_lon[0]},{max_lat_lon[1]});
    way["{keyword}"]({min_lat_lon[0]},{min_lat_lon[1]},{max_lat_lon[0]},{max_lat_lon[1]});
    relation["{keyword}"]({min_lat_lon[0]},{min_lat_lon[1]},{max_lat_lon[0]},{max_lat_lon[1]});
    );out body;>;out skel qt;"""

    response = requests.get(overpass_url, params={"data": overpass_query})
    data = response.json()
    features = data["elements"]

    return features


def get_buildings(
    lat: float, lon: float, r: float, angle_rad: float, units: float
) -> list[Base]:
    """Get a list of 3d Meshes of buildings by lat&lon (degrees) and radius (meters)."""
    # https://towardsdatascience.com/loading-data-from-openstreetmap-with-python-and-the-overpass-api-513882a27fd0

    scale_factor = get_scale_factor_to_meters(units)

    keyword = "building"
    min_lat_lon, max_lat_lon = get_degrees_bbox_from_lat_lon_rad(lat, lon, r)
    features = get_features_from_osm_server(keyword, min_lat_lon, max_lat_lon)

    ways = []
    tags = []
    rel_outer_ways = []
    rel_outer_ways_tags = []
    rel_inner_ways = []
    ways_part = []
    nodes = []

    for feature in features:
        # ways
        if feature["type"] == "way":
            try:
                feature["id"]
                feature["nodes"]

                try:
                    tags.append(
                        {
                            f"{keyword}": feature["tags"][keyword],
                            "height": feature["tags"]["height"],
                        }
                    )
                except:
                    try:
                        tags.append(
                            {
                                f"{keyword}": feature["tags"][keyword],
                                "levels": feature["tags"]["building:levels"],
                            }
                        )
                    except:
                        try:
                            tags.append(
                                {
                                    f"{keyword}": feature["tags"][keyword],
                                    "layer": feature["tags"]["layer"],
                                }
                            )
                        except:
                            tags.append({f"{keyword}": feature["tags"][keyword]})
                ways.append(
                    {
                        "nodes": feature["nodes"],
                        "inner_nodes": [],
                    }  # "id": feature["id"],
                )
            except:
                ways_part.append({"id": feature["id"], "nodes": feature["nodes"]})

        # relations
        elif feature["type"] == "relation":
            outer_ways = []
            inner_ways = []
            try:
                outer_ways_tags = {
                    f"{keyword}": feature["tags"][keyword],
                    "height": feature["tags"]["height"],
                }
            except:
                try:
                    outer_ways_tags = {
                        f"{keyword}": feature["tags"][keyword],
                        "levels": feature["tags"]["building:levels"],
                    }
                except:
                    try:
                        outer_ways_tags = {
                            f"{keyword}": feature["tags"][keyword],
                            "layer": feature["tags"]["layer"],
                        }
                    except:
                        outer_ways_tags = {f"{keyword}": feature["tags"][keyword]}

            for n, x in enumerate(feature["members"]):
                # if several Outer ways, combine them
                if (
                    feature["members"][n]["type"] == "way"
                    and feature["members"][n]["role"] == "outer"
                ):
                    outer_ways.append({"ref": feature["members"][n]["ref"]})
                elif (
                    feature["members"][n]["type"] == "way"
                    and feature["members"][n]["role"] == "inner"
                ):
                    inner_ways.append({"ref": feature["members"][n]["ref"]})
            rel_outer_ways.append(outer_ways)
            rel_outer_ways_tags.append(outer_ways_tags)
            rel_inner_ways.append(inner_ways)

        # get nodes (that don't have tags)
        elif feature["type"] == "node":
            try:
                feature["tags"]
            except:
                nodes.append(
                    {"id": feature["id"], "lat": feature["lat"], "lon": feature["lon"]}
                )

    # turn relations_OUTER into ways
    for n, x in enumerate(rel_outer_ways):  # just 1
        # there will be a list of "ways" in each of rel_outer_ways
        full_node_list = []
        full_node_inner_list = []
        for m, y in enumerate(rel_outer_ways[n]):
            # find ways_parts with corresponding ID
            for k, z in enumerate(ways_part):
                if k == len(ways_part):
                    break

                if rel_outer_ways[n][m]["ref"] == ways_part[k]["id"]:
                    # reverse way part is needed
                    node_list = ways_part[k]["nodes"].copy()
                    if (
                        len(full_node_list) > 0
                        and full_node_list[len(full_node_list) - 1] != node_list[0]
                    ):
                        node_list.reverse()
                    node_list = [
                        n
                        for j, n in enumerate(node_list)
                        if (n not in full_node_list or j == len(node_list) - 1)
                    ]

                    full_node_list += node_list
                    item = ways_part.pop(k)  # remove used ways_parts
                    ways_part.append(item)
                    k -= 1  # reset index
                    break

        for m, y in enumerate(rel_inner_ways[n]):
            # find ways_parts with corresponding ID
            local_node_list = []
            for k, z in enumerate(ways_part):
                if k == len(ways_part):
                    break
                if rel_inner_ways[n][m]["ref"] == ways_part[k]["id"]:
                    # if rel_inner_ways[n][m]["ref"] == 260719444:
                    #    print(f"{ways_part[k]['nodes']}")
                    # reverse way part is needed
                    node_list = ways_part[k]["nodes"].copy()
                    if (
                        len(local_node_list) > 0
                        and local_node_list[len(local_node_list) - 1] != node_list[0]
                    ):
                        node_list.reverse()
                    node_list = [
                        n
                        for j, n in enumerate(node_list)
                        if (n not in local_node_list or j == len(node_list) - 1)
                    ]

                    local_node_list += node_list  # ways_part[k]["nodes"]
                    item = ways_part.pop(k)  # remove used ways_parts
                    ways_part.append(item)
                    k -= 1  # reset index
                    break
            full_node_inner_list.append(local_node_list)

        ways.append({"nodes": full_node_list, "inner_nodes": full_node_inner_list})
        try:
            tags.append(
                {
                    f"{keyword}": rel_outer_ways_tags[n][keyword],
                    "height": rel_outer_ways_tags[n]["height"],
                }
            )
        except:
            try:
                tags.append(
                    {
                        f"{keyword}": rel_outer_ways_tags[n][keyword],
                        "levels": rel_outer_ways_tags[n]["levels"],
                    }
                )
            except:
                try:
                    tags.append(
                        {
                            f"{keyword}": rel_outer_ways_tags[n][keyword],
                            "layer": rel_outer_ways_tags[n]["layer"],
                        }
                    )
                except:
                    tags.append({f"{keyword}": rel_outer_ways_tags[n][keyword]})

    projected_crs = create_crs(lat, lon)

    # get coords of Ways
    objectGroup = []
    for i, x in enumerate(ways):
        ids = ways[i]
        coords = []  # replace node IDs with actual coords for each Way
        coords_inner = []
        height = 9
        try:
            # height = float(tags[i]["height"])
            height = float(clean_string(tags[i]["height"].split(",")[0].split(";")[0]))
        except:
            try:
                # height = float(tags[i]["levels"]) * 3
                height = (
                    float(clean_string(tags[i]["levels"].split(",")[0].split(";")[0]))
                    * 3
                )
            except:
                try:
                    if (
                        # float(tags[i]["layer"])
                        float(
                            clean_string(tags[i]["layer"].split(",")[0].split(";")[0])
                        )
                        < 0
                    ):
                        height *= -1
                except:
                    pass
        height /= scale_factor

        # go through each external node of the Way
        for k, _ in enumerate(ids["nodes"]):
            if k == len(ids["nodes"]) - 1:
                continue  # ignore last
            for n, z in enumerate(nodes):  # go though all nodes
                if ids["nodes"][k] == nodes[n]["id"]:
                    x, y = reproject_to_crs(
                        nodes[n]["lat"], nodes[n]["lon"], "EPSG:4326", projected_crs
                    )
                    coords.append({"x": x / scale_factor, "y": y / scale_factor})
                    break

        # go through each internal node of the Way
        for l, void_nodes in enumerate(ids["inner_nodes"]):
            coords_per_void = []
            for k, node_list in enumerate(void_nodes):
                if k == len(ids["inner_nodes"][l]) - 1:
                    continue  # ignore last
                for n, z in enumerate(nodes):  # go though all nodes
                    if ids["inner_nodes"][l][k] == nodes[n]["id"]:
                        x, y = reproject_to_crs(
                            nodes[n]["lat"], nodes[n]["lon"], "EPSG:4326", projected_crs
                        )
                        coords_per_void.append(
                            {"x": x / scale_factor, "y": y / scale_factor}
                        )
                        break
            coords_inner.append(coords_per_void)

        if angle_rad == 0:
            obj = extrude_building(coords, coords_inner, height)
        else:
            rotated_coords = [rotate_pt(c, angle_rad) for c in coords]
            rotated_coords_inner = [
                [rotate_pt(c_void, angle_rad) for c_void in c] for c in coords_inner
            ]
            obj = extrude_building(rotated_coords, rotated_coords_inner, height)

        if obj is not None:
            obj.units = units
            base_obj = Base(
                units=units,
                displayValue=[obj],
                building=tags[i]["building"],
                sourceData="© OpenStreetMap",
                sourceUrl="https://www.openstreetmap.org/",
            )
            objectGroup.append(base_obj)  # (obj, tags[i]["building"]))

        coords = None
        height = None

    return objectGroup


def get_roads(
    lat: float, lon: float, r: float, angle_rad: float, units: float
) -> tuple[list[Base]]:
    """Get a list of Polylines and Meshes of roads by lat&lon (degrees) and radius (meters)."""
    scale_factor = get_scale_factor_to_meters(units)
    keyword = "highway"
    min_lat_lon, max_lat_lon = get_degrees_bbox_from_lat_lon_rad(lat, lon, r)
    features = get_features_from_osm_server(keyword, min_lat_lon, max_lat_lon)

    ways = []
    tags = []
    rel_outer_ways = []
    rel_outer_ways_tags = []
    ways_part = []
    nodes = []

    for feature in features:
        # ways
        if feature["type"] == "way":
            try:
                feature["id"]
                feature["nodes"]

                tags.append({f"{keyword}": feature["tags"][keyword]})
                ways.append({"id": feature["id"], "nodes": feature["nodes"]})
            except:
                ways_part.append({"id": feature["id"], "nodes": feature["nodes"]})

        # relations
        elif feature["type"] == "relation":
            outer_ways = []
            try:
                outer_ways_tags = {
                    f"{keyword}": feature["tags"][keyword],
                    "area": feature["tags"]["area"],
                }
            except:
                outer_ways_tags = {f"{keyword}": feature["tags"][keyword]}

            for n, x in enumerate(feature["members"]):
                # if several Outer ways, combine them
                if feature["members"][n]["type"] == "way":
                    outer_ways.append({"ref": feature["members"][n]["ref"]})

            rel_outer_ways.append(outer_ways)
            rel_outer_ways_tags.append(outer_ways_tags)

        # get nodes (that don't have tags)
        elif feature["type"] == "node":
            try:
                feature["tags"]
                feature["tags"][keyword]
            except:
                nodes.append(
                    {"id": feature["id"], "lat": feature["lat"], "lon": feature["lon"]}
                )

    # turn relations_OUTER into ways
    for n, x in enumerate(rel_outer_ways):
        # there will be a list of "ways" in each of rel_outer_ways
        full_node_list = []
        for m, y in enumerate(rel_outer_ways[n]):
            # find ways_parts with corresponding ID
            for k, z in enumerate(ways_part):
                if k == len(ways_part):
                    break
                if rel_outer_ways[n][m]["ref"] == ways_part[k]["id"]:
                    full_node_list += ways_part[k]["nodes"]
                    ways_part.pop(k)  # remove used ways_parts
                    k -= 1  # reset index
                    break

            # move inside the loop to separate the sections
            ways.append({"nodes": full_node_list})
            try:
                tags.append(
                    {
                        f"{keyword}": rel_outer_ways_tags[n][keyword],
                        "area": rel_outer_ways_tags[n]["area"],
                    }
                )
            except:
                tags.append({f"{keyword}": rel_outer_ways_tags[n][keyword]})
            # empty the list after each loop to start new part
            full_node_list = []

    projected_crs = create_crs(lat, lon)

    # get coords of Ways
    objectGroup = []
    meshGroup = []

    ways, tags = split_ways_by_intersection(ways, tags)

    for i, x in enumerate(ways):  # go through each Way: 2384
        ids = ways[i]["nodes"]
        coords = []  # replace node IDs with actual coords for each Way

        value = 2 / scale_factor
        if tags[i][keyword] in ["primary"]:
            value = 9 / scale_factor
        elif tags[i][keyword] in ["secondary"]:
            value = 6 / scale_factor
        try:
            if tags[i]["area"] == "yes":
                value = None
                continue
        except:
            pass

        closed = False
        for k, y in enumerate(ids):  # go through each node of the Way
            if k == len(ids) - 1 and y == ids[0]:
                closed = True
                continue
            for n, z in enumerate(nodes):  # go though all nodes
                if ids[k] == nodes[n]["id"]:
                    x, y = reproject_to_crs(
                        nodes[n]["lat"], nodes[n]["lon"], "EPSG:4326", projected_crs
                    )
                    coords.append({"x": x / scale_factor, "y": y / scale_factor})
                    break

        if angle_rad == 0:
            obj = join_roads(coords, closed, 0)
        else:
            rotated_coords = [rotate_pt(c, angle_rad) for c in coords]
            obj = join_roads(rotated_coords, closed, 0)
            obj.units = units
        objectGroup.append(obj)

        objMesh = road_buffer(obj, value, elevation=0.02 / scale_factor)
        objMesh.units = units
        for mesh in objMesh.displayValue:
            mesh.units = units
        if objMesh is not None:  # filter out ignored "areas"
            meshGroup.append(objMesh)

    return objectGroup, meshGroup


def get_nature(
    lat: float, lon: float, r: float, angle_rad: float, units: float
) -> list[Base]:
    """Get a list of 3d Meshes of buildings by lat&lon (degrees) and radius (meters)."""
    # https://towardsdatascience.com/loading-data-from-openstreetmap-with-python-and-the-overpass-api-513882a27fd0
    scale_factor = get_scale_factor_to_meters(units)
    features = []
    all_keywords = ["landuse", "natural", "leisure"]

    for keyword in all_keywords:
        min_lat_lon, max_lat_lon = get_degrees_bbox_from_lat_lon_rad(lat, lon, r)
        features_part = get_features_from_osm_server(keyword, min_lat_lon, max_lat_lon)
        features.extend(features_part)

    ways = []
    tags = []
    rel_outer_ways = []
    rel_outer_ways_tags = []
    ways_part = []
    nodes = []

    all_landuse_polygons = ["forest", "meadow", "grass"]
    all_natural_polygons = ["scrub", "grassland"]
    all_leisure_polygons = ["nature_reserve", "garden", "park", "playground"]
    all_green_polygons = (
        all_landuse_polygons + all_natural_polygons + all_leisure_polygons
    )
    trees_nodes = []  # natural: tree, natural: tree_row,

    objectGroup = []
    for keyword in all_keywords:
        tree_rows = []
        for feature in features:
            trees = ""
            # ways
            if feature["type"] == "way":
                try:
                    if feature["tags"][keyword] == "tree_row":
                        tree_rows.append({"nodes": feature["nodes"]})
                    if feature["tags"][keyword] == "forest":
                        trees = "trees"

                    if feature["tags"][keyword] not in all_green_polygons:
                        continue
                    feature["id"]
                    feature["nodes"]
                    tags.append(
                        {f"{keyword}": feature["tags"][keyword], "trees": trees}
                    )
                    ways.append(
                        {
                            "nodes": feature["nodes"],
                        }
                    )
                except:
                    ways_part.append({"id": feature["id"], "nodes": feature["nodes"]})

            # relations
            elif feature["type"] == "relation":
                try:
                    if feature["tags"][keyword] == "tree_row":
                        tree_rows.append({"nodes": feature["nodes"]})
                    if feature["tags"][keyword] == "forest":
                        trees = "trees"

                    if feature["tags"][keyword] not in all_green_polygons:
                        continue
                    outer_ways = []
                    outer_ways_tags = {
                        f"{keyword}": feature["tags"][keyword],
                        "trees": trees,
                    }

                    for n, x in enumerate(feature["members"]):
                        # if several Outer ways, combine them
                        if (
                            feature["members"][n]["type"] == "way"
                            and feature["members"][n]["role"] == "outer"
                        ):
                            outer_ways.append({"ref": feature["members"][n]["ref"]})

                    rel_outer_ways.append(outer_ways)
                    rel_outer_ways_tags.append(outer_ways_tags)
                except:
                    pass

            # get nodes (that don't have tags)
            elif feature["type"] == "node":
                try:
                    # consider trees yet
                    feature["tags"]
                    if feature["tags"][keyword] == "tree":
                        trees_nodes.append(
                            {
                                "id": feature["id"],
                                "tree": feature["tags"][keyword],
                                "lat": feature["lat"],
                                "lon": feature["lon"],
                            }
                        )
                except:
                    nodes.append(
                        {
                            "id": feature["id"],
                            "lat": feature["lat"],
                            "lon": feature["lon"],
                        }
                    )

        # turn relations_OUTER into ways
        for n, x in enumerate(rel_outer_ways):
            # there will be a list of "ways" in each of rel_outer_ways
            full_node_list = []
            for m, y in enumerate(rel_outer_ways[n]):
                # find ways_parts with corresponding ID
                for k, z in enumerate(ways_part):
                    if k == len(ways_part):
                        break

                    if rel_outer_ways[n][m]["ref"] == ways_part[k]["id"]:
                        # reverse way part is needed
                        node_list = ways_part[k]["nodes"].copy()
                        if (
                            len(full_node_list) > 0
                            and full_node_list[len(full_node_list) - 1] != node_list[0]
                        ):
                            node_list.reverse()
                        node_list = [
                            n
                            for j, n in enumerate(node_list)
                            if (n not in full_node_list or j == len(node_list) - 1)
                        ]

                        full_node_list += node_list
                        item = ways_part.pop(k)  # remove used ways_parts
                        ways_part.append(item)
                        k -= 1  # reset index
                        break

            ways.append({"nodes": full_node_list})
            tags.append(
                {
                    f"{keyword}": rel_outer_ways_tags[n][keyword],
                    "trees": rel_outer_ways_tags[n]["trees"],
                }
            )
        projected_crs = create_crs(lat, lon)

        # get coords of Ways - polygons
        for i, x in enumerate(ways):
            ids = ways[i]
            coords = []  # replace node IDs with actual coords for each Way
            tree_polygon = []

            # go through each external node of the Way
            for k, _ in enumerate(ids["nodes"]):
                if k == len(ids["nodes"]) - 1:
                    continue  # ignore last
                for n, z in enumerate(nodes):  # go though all nodes
                    if ids["nodes"][k] == nodes[n]["id"]:
                        # tree_polygon
                        if tags[i]["trees"] != "":
                            tree_polygon.append((nodes[n]["lon"], nodes[n]["lat"]))

                        x, y = reproject_to_crs(
                            nodes[n]["lat"], nodes[n]["lon"], "EPSG:4326", projected_crs
                        )
                        coords.append({"x": x / scale_factor, "y": y / scale_factor})
                        break

            if len(tree_polygon) > 3:
                new_tree_pts = generate_points_inside_polygon(tree_polygon)
                for pt in new_tree_pts:
                    trees_nodes.append({"id": "forest", "lon": pt[0], "lat": pt[1]})

            if angle_rad == 0:
                obj = create_flat_mesh(coords, elevation=0.01)
            else:
                rotated_coords = [rotate_pt(c, angle_rad) for c in coords]
                obj = create_flat_mesh(rotated_coords, elevation=0.01)
            obj.units = units

            if obj is not None:
                for keyword in all_keywords:
                    try:  # iterate through keywords
                        base_obj = Base(
                            units=units,
                            displayValue=[obj],
                            keyword=tags[i][keyword],
                            sourceData="© OpenStreetMap",
                            sourceUrl="https://www.openstreetmap.org/",
                        )
                        objectGroup.append(base_obj)  # (obj, tags[i]["building"]))
                        break
                    except:
                        pass
            coords = None

        # get coords of Ways - tree rows
        for i, ids in enumerate(tree_rows):
            coords_tree_row = []  # replace node IDs with actual coords for each Way
            # go through each node of the Way
            for k, _ in enumerate(ids["nodes"]):
                for n, z in enumerate(nodes):  # go though all nodes
                    if ids["nodes"][k] == nodes[n]["id"]:
                        new_item = {
                            "id": nodes[n]["id"],
                            "y": nodes[n]["lat"],
                            "x": nodes[n]["lon"],
                        }
                        if new_item not in coords_tree_row:
                            coords_tree_row.append(new_item)
                        break

            for w, pt in enumerate(coords_tree_row):
                trees_nodes.append({"id": pt["id"], "lon": pt["x"], "lat": pt["y"]})

    # generate trees:
    for tree in trees_nodes:
        x, y = reproject_to_crs(tree["lat"], tree["lon"], "EPSG:4326", projected_crs)
        coords_tree = {"x": x / scale_factor, "y": y / scale_factor}

        if angle_rad == 0:
            tree_elements = generate_tree(
                tree, coords_tree, scale_factor, elevation=0.025 / scale_factor
            )
        else:
            rotated_coords = rotate_pt(coords_tree, angle_rad)
            tree_elements = generate_tree(
                tree, rotated_coords, scale_factor, elevation=0.025 / scale_factor
            )

        elements = []
        for item in tree_elements:
            if item is not None:
                item.units = units
                elements.append(item)

        base_obj = Base(
            units=units,
            displayValue=elements,
            natural="tree",
            sourceData="© OpenStreetMap",
            sourceUrl="https://www.openstreetmap.org/",
        )
        objectGroup.append(base_obj)

    return objectGroup
