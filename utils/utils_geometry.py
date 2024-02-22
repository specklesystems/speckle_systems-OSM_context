"""Operations with geometry."""

import math
import random

import geopandas as gpd
import numpy as np
from geovoronoi import voronoi_regions_from_coords
from shapely import Point as shapely_Point
from shapely import Polygon as shapely_Polygon
from shapely.affinity import affine_transform
from shapely.ops import triangulate
from specklepy.objects.geometry import Point, Polyline

from utils.utils_other import split_list_by_repeated_elements


def fix_polygon_orientation(
    point_tuple_list: list[tuple[float | int, float | int]],
    vert_indices: list[int],
    make_clockwise_facing_down: bool = True,
    coef: int = 1,
) -> tuple[list, bool]:
    """Check the polygon face orientation and reverse if needed.

    Args:
        point_tuple_list: list of points' coordinates as tuples
        vert_indices: ordered indices of the polygon vertices
        make_clockwise_facing_down: output polygon orientation
        coef: simplification coefficient for large polygons

    Returns:
        Tuple: (List of (re)ordered vertices' indices,
        boolean True if polygon was originally clockwise).
    """
    sum_orientation: float | int = 0
    for i, _ in enumerate(point_tuple_list):
        if i * coef >= len(point_tuple_list):
            break

        next_index = i + 1
        if next_index * coef >= len(point_tuple_list) - 1:
            next_index = 0
        pt = point_tuple_list[i * coef]
        pt2 = point_tuple_list[next_index * coef]

        sum_orientation += (pt2[0] - pt[0]) * (pt2[1] + pt[1])

    if sum_orientation > 0:  # facing down originally
        return vert_indices, True

    # facing up originally
    # if needs to be facing down, reverse the vertex order
    if make_clockwise_facing_down:
        vert_indices.reverse()

    return vert_indices, False


def create_side_face(
    coords: list[dict],
    index: int,
    height: float | int,
    clockwise_orientation: bool,
) -> list[float]:
    """Construct vertical Mesh face (wall) facing outside the building.

    Args:
        coords: list of points' coordinates as dict {"x":x, "y":y}
        index: index of the polygon vertex to start an edge extrusion
        height: height of the extrusion
        clockwise_orientation: True if polygon has clockwise orientation

    Returns:
        Flat list of ordered vertex coordinates (e.g. [x0,y0,z0,x1,y1,z1..])

    Raises:
        IndexError: If vertex index is out of range.
    """
    if index == len(coords) - 1:
        next_coord_index = 0
    elif index < len(coords) - 1:
        next_coord_index = index + 1
    else:
        raise IndexError(f"Index '{index}' is out of range ({len(coords)} points)")

    next_coord = coords[next_coord_index]
    if clockwise_orientation is False:  # if counter-clockwise orientation
        side_vertices = [
            coords[index]["x"],
            coords[index]["y"],
            0,
            next_coord["x"],
            next_coord["y"],
            0,
            next_coord["x"],
            next_coord["y"],
            height,
            coords[index]["x"],
            coords[index]["y"],
            height,
        ]
    else:  # if clockwise orientation
        side_vertices = [
            coords[index]["x"],
            coords[index]["y"],
            0,
            coords[index]["x"],
            coords[index]["y"],
            height,
            next_coord["x"],
            next_coord["y"],
            height,
            next_coord["x"],
            next_coord["y"],
            0,
        ]

    return side_vertices


def to_triangles(
    coords: list[dict],
    coords_inner: list[list[dict]],
    attempt: int = 0,
) -> tuple[dict | None, int | None]:
    """Generate triangular faces from the Polygon with voids.

    Args:
        coords: list of boundary points' coordinates as dict {"x":x, "y":y}
        coords_inner: list of voids with list of points' coords as dict {"x":x, "y":y}
        attempt: iteration of geometry simplification in case of failed triangulation

    Returns:
        Tuple: (dict with triangulated data, attempt of triangulation)
    """
    # https://gis.stackexchange.com/questions/316697/delaunay-triangulation-algorithm-in-shapely-producing-erratic-result
    try:
        digits = 3 - attempt

        # round vertices precision
        vert = []
        vert_rounded = []
        # round boundary precision:
        for i, coord_dict in enumerate(coords):
            if i == len(coords) - 1:
                vert.append((coord_dict["x"], coord_dict["y"]))
                break  # don't test last point
            # if any previous vertext with similar rounded value has
            # been added before, then ignore
            rounded = [round(coord_dict[key], digits) for key in ["x", "y"]]
            if coord_dict not in vert and rounded not in vert_rounded:
                vert.append((coord_dict["x"], coord_dict["y"]))
                vert_rounded.append(rounded)
        # round courtyards precision:
        holes = []
        holes_rounded = []
        for coord_inner_single in coords_inner:
            hole = []
            for i, coord_dict in enumerate(coord_inner_single):
                if i == len(coord_inner_single) - 1:
                    hole.append((coord_dict["x"], coord_dict["y"]))
                    break  # don't test last point
                # if any previous vertext with similar rounded value has
                # been added before, then ignore
                rounded = [round(coord_dict[key], digits) for key in ["x", "y"]]
                if coord_dict not in holes and rounded not in holes_rounded:
                    hole.append((coord_dict["x"], coord_dict["y"]))
                    holes_rounded.append(rounded)
            holes.append(hole)

        # check if sufficient holes vertices were added
        if len(holes) == 1 and len(holes[0]) == 0:
            polygon = shapely_Polygon([(v) for v in vert])
        else:
            polygon = shapely_Polygon([(v) for v in vert], holes)

        # add porder points
        try:
            exterior_linearring = polygon.buffer(-0.001).exterior
        except AttributeError:
            exterior_linearring = polygon.buffer(-0.0001).exterior
        poly_points = np.array(exterior_linearring.coords).tolist()

        # add voids'points
        try:
            polygon.interiors[0]
            for i, interior_linearring in enumerate(polygon.interiors):
                a = interior_linearring.coords
                poly_points += np.array(a).tolist()
        except Exception:
            pass

        poly_points = np.array(
            [item for sublist in poly_points for item in sublist]
        ).reshape(-1, 2)

        poly_shapes, _ = voronoi_regions_from_coords(poly_points, polygon.buffer(0))
        gdf_poly_voronoi = (
            gpd.GeoDataFrame({"geometry": poly_shapes})
            .explode(index_parts=True)
            .reset_index()
        )

        vertices = []
        triangles = []
        for geom in gdf_poly_voronoi.geometry:
            for tri in triangulate(geom):
                if not tri.centroid.within(polygon):
                    continue
                xx, yy = tri.exterior.coords.xy

                vert_indices_in_triangle = []
                count = 0
                for vt in zip(xx.tolist(), yy.tolist()):
                    v = list(vt)
                    if count == 3:
                        continue
                    if v not in vertices:
                        vertices.append(v)
                        vert_indices_in_triangle.append(len(vertices) - 1)
                    else:
                        vert_indices_in_triangle.append(vertices.index(v))
                    count += 1
                triangles.append(vert_indices_in_triangle)

        shape = {"vertices": vertices, "triangles": triangles}
        return shape, attempt
    except Exception as e:
        print(f"Meshing iteration {attempt} failed: {e}")
        attempt += 1
        if attempt <= 3:
            return to_triangles(coords, coords_inner, attempt)
        else:
            return None, None


def rotate_pt(coord: dict, angle_rad: float | int) -> dict:
    """Rotate a point around (0,0,1) axis."""
    x = coord["x"]
    y = coord["y"]
    x2 = x * math.cos(angle_rad) + y * math.sin(angle_rad)
    y2 = -x * math.sin(angle_rad) + y * math.cos(angle_rad)

    return {"x": x2, "y": y2}


def split_ways_by_intersection(
    ways: list[dict],
    tags: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Separate ways and tags into different lists if they self-intersect."""
    splitWays = []
    splitTags = []

    for i, w in enumerate(ways):
        ids = w["nodes"]
        try:
            if tags[i]["area"] == "yes":
                splitWays.append(w)
                splitTags.append(tags[i])
                continue  # don't look for intersections
        except KeyError:
            pass

        if len(ids) == 0 or len(list(set(ids))) < len(ids):  # if there are repetitions
            wList = split_list_by_repeated_elements(ids, [])
            for item in wList:
                x: dict = {"nodes": item}
                splitWays.append(x)
                splitTags.append(tags[i])
        else:
            splitWays.append(w)
            splitTags.append(tags[i])

    return splitWays, splitTags


def join_roads(coords: list[dict], closed: bool) -> Polyline:
    """Create a Polyline from a list of coordinates."""
    points = []

    for c in coords:
        points.append(Point.from_list([c["x"], c["y"], 0]))

    poly = Polyline.from_points(points)
    poly.closed = closed
    # poly.units = "m"
    poly.sourceData = "© OpenStreetMap"
    poly.sourceUrl = "https://www.openstreetmap.org/"

    return poly


def generate_points_inside_polygon(
    polygon_pts: list[tuple], point_number: int = 3
) -> list[tuple[float]]:
    """Populate polygon with points."""
    # https://codereview.stackexchange.com/questions/69833/generate-sample-coordinates-inside-a-polygon

    polygon = shapely_Polygon(polygon_pts)
    areas = []
    transforms = []
    for t in triangulate(polygon):
        areas.append(t.area)
        (x0, y0), (x1, y1), (x2, y2), _ = t.exterior.coords
        transforms.append([x1 - x0, x2 - x0, y2 - y0, y1 - y0, x0, y0])
    points = []
    for transform in random.choices(transforms, weights=areas, k=point_number):
        x, y = [random.random() for _ in range(2)]
        if x + y > 1:
            p = shapely_Point(1 - x, 1 - y)
        else:
            p = shapely_Point(x, y)
        points.append(affine_transform(p, transform))
    # coords = np.array([p.coords for p in points]).reshape(-1, 2)
    coords: list[tuple[float]] = [p.coords[0] for p in points]
    return coords
