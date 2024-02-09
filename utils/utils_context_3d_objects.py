"""Generation of the 3d objects from OSM data."""

import json
import math
import random

from shapely import (
    LineString,
    buffer,
    to_geojson,
)
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh, Polyline

from assets.trees import COLORS, FACES, TEXTURE_COORDS, VERTICES
from utils.utils_geometry import (
    create_side_face,
    fix_polygon_orientation,
    rotate_pt,
    to_triangles,
)
from utils.utils_other import (
    COLOR_BLD,
    COLOR_GREEN,
    COLOR_ROAD,
    COLOR_TREE_BASE,
    COLOR_TREE_BASE_BROWN,
)


def create_flat_mesh(
    coords: list[dict], color: int | None = None, elevation: float = 0.01
) -> Mesh:
    """Create a polygon facing up, no voids."""
    if len(coords) < 3:
        return None
    vertices = []
    faces = []
    colors = []
    if color is None:  # apply green
        color = COLOR_GREEN

    # bottom
    bottom_vert_indices = list(range(len(coords)))
    bottom_vertices = [(c["x"], c["y"]) for c in coords]
    bottom_vert_indices, _ = fix_polygon_orientation(bottom_vertices, bottom_vert_indices)
    bottom_vert_indices.reverse()

    for c in coords:
        vertices.extend([c["x"], c["y"], elevation])
        colors.append(color)
    faces.extend([len(coords)] + bottom_vert_indices)

    obj = Mesh.create(faces=faces, vertices=vertices, colors=colors)
    # obj.units = "m"

    return obj


def extrude_building_simple(coords: list[dict], height: float | int) -> Mesh:
    """Create 3D Mesh from lists of outer and inner coords & height."""
    vertices = []
    faces = []
    colors = []

    color = COLOR_BLD  # (255<<24) + (100<<16) + (100<<8) + 100 # argb

    if len(coords) < 3:
        return None

    # bottom
    bottom_vert_indices = list(range(len(coords)))
    bottom_vertices = [(c["x"], c["y"]) for c in coords]
    bottom_vert_indices, clockwise_orientation = fix_polygon_orientation(
        bottom_vertices, bottom_vert_indices
    )
    for c in coords:
        vertices.extend([c["x"], c["y"], 0])
        colors.append(color)
    faces.extend([len(coords)] + bottom_vert_indices)

    # top
    top_vert_indices = list(range(len(coords), 2 * len(coords)))
    for c in coords:
        vertices.extend([c["x"], c["y"], height])
        colors.append(color)

    if clockwise_orientation is True:  # if facing down originally
        top_vert_indices.reverse()
    faces.extend([len(coords)] + top_vert_indices)

    # sides
    total_vertices = len(colors)
    for i, c in enumerate(coords):
        side_vert_indices = list(range(total_vertices, total_vertices + 4))
        faces.extend([4] + side_vert_indices)
        side_vertices = create_side_face(coords, i, height, clockwise_orientation)
        vertices.extend(side_vertices)
        colors.extend([color, color, color, color])
        total_vertices += 4

    obj = Mesh.create(faces=faces, vertices=vertices, colors=colors)
    # obj.units = "m"

    return obj


def extrude_building_complex(
    coords: list[dict], coords_inner: list[list[dict]], height: float | int
) -> Mesh:
    """Create a 3d Mesh from the lists of outer and inner coords and height."""
    vertices = []
    faces = []
    colors = []

    color = COLOR_BLD  # (255<<24) + (100<<16) + (100<<8) + 100 # argb

    if len(coords) < 3:
        return None
    # bottom
    try:
        total_vertices = 0
        triangulated_geom, _ = to_triangles(coords, coords_inner)
    except Exception as e:  # default to only outer border mesh generation
        print(f"Mesh creation failed: {e}")
        return extrude_building_simple(coords, height)

    if triangulated_geom is None:  # default to only outer border mesh generation
        return extrude_building_simple(coords, height)

    pt_list = [[p[0], p[1], 0] for p in triangulated_geom["vertices"]]
    triangle_list = [trg for trg in triangulated_geom["triangles"]]

    for trg in triangle_list:
        a = trg[0]
        b = trg[1]
        c = trg[2]
        vertices.extend(pt_list[a] + pt_list[b] + pt_list[c])
        colors.extend([color, color, color])
        total_vertices += 3

        # all faces are counter-clockwise now (facing up)
        # therefore, add vertices in the reverse (clockwise) order (facing down)
        faces.extend([3, total_vertices - 1, total_vertices - 2, total_vertices - 3])

    # top
    pt_list = [[p[0], p[1], height] for p in triangulated_geom["vertices"]]

    for trg in triangle_list:
        a = trg[0]
        b = trg[1]
        c = trg[2]
        # all faces are counter-clockwise now (facing up)
        vertices.extend(pt_list[a] + pt_list[b] + pt_list[c])
        colors.extend([color, color, color])
        total_vertices += 3
        faces.extend([3, total_vertices - 3, total_vertices - 2, total_vertices - 1])

    # sides
    bottom_vert_indices = list(range(len(coords)))
    bottom_vertices = [(c["x"], c["y"]) for c in coords]
    bottom_vert_indices, clockwise_orientation = fix_polygon_orientation(
        bottom_vertices, bottom_vert_indices
    )
    for i, c in enumerate(coords):
        side_vert_indices = list(range(total_vertices, total_vertices + 4))
        faces.extend([4] + side_vert_indices)
        side_vertices = create_side_face(coords, i, height, clockwise_orientation)

        vertices.extend(side_vertices)
        colors.extend([color, color, color, color])
        total_vertices += 4

    # voids sides
    for _, local_coords_inner in enumerate(coords_inner):
        bottom_void_vert_indices = list(range(len(local_coords_inner)))
        bottom_void_vertices = [[c["x"], c["y"]] for c in local_coords_inner]
        bottom_void_vert_indices, clockwise_orientation_void = fix_polygon_orientation(
            bottom_void_vertices, bottom_void_vert_indices
        )

        for i, c in enumerate(local_coords_inner):
            side_vert_indices = list(range(total_vertices, total_vertices + 4))
            faces.extend([4] + side_vert_indices)
            side_vertices = create_side_face(
                local_coords_inner,
                i,
                height,
                clockwise_orientation_void,
            )
            vertices.extend(side_vertices)
            colors.extend([color, color, color, color])
            total_vertices += 4

    obj = Mesh.create(faces=faces, vertices=vertices, colors=colors)
    # obj.units = "m"

    return obj


def extrude_building(
    coords: list[dict], coords_inner: list[list[dict]], height: float | int
) -> Mesh:
    """Create a 3d Mesh from the lists of outer and inner coords and height."""
    if len(coords) < 3:
        return None
    if len(coords_inner) == 0:
        return extrude_building_simple(coords, height)
    else:
        return extrude_building_complex(coords, coords_inner, height)


def generate_tree(
    tree: dict, coords: dict, scale_factor, elevation=0.025
) -> list[Mesh]:
    """Create a 3d tree in a given location."""
    obj = None
    tree_base = None
    tree_base_top = None
    scale = random.randint(80, 140) / 100 / scale_factor
    scale_z = random.randint(80, 140) / 100 / scale_factor
    if tree["id"] == "forest":
        scale *= 2
        scale_z *= 2
    angle_rad = random.randint(-200, 200) / 100
    try:
        vertices = []
        for i in range(int(len(VERTICES) / 3)):
            xy = rotate_pt(
                {"x": VERTICES[3 * i] * scale, "y": VERTICES[3 * i + 1] * scale},
                angle_rad,
            )
            vertices.append(xy["x"] + coords["x"])
            vertices.append(xy["y"] + coords["y"])
            vertices.append(VERTICES[3 * i + 2] * scale_z)

        obj = Mesh.create(
            faces=FACES,
            vertices=vertices,
            colors=COLORS,
            texture_coordinates=TEXTURE_COORDS,
        )
        # obj.units = "m"

        if tree["id"] != "forest":
            # generate base bottom
            color = COLOR_TREE_BASE_BROWN
            vertices = []
            colors = []
            border_pt = {"x": 1 / scale_factor, "y": 0}
            steps = 12
            for s in range(steps):
                k = -1 * s / steps
                new_pt = rotate_pt(border_pt, 2 * math.pi * k)
                colors.append(color)
                vertices.extend(
                    [new_pt["x"] + coords["x"], new_pt["y"] + coords["y"], elevation]
                )
            faces = [steps] + list(range(steps))
            tree_base = Mesh.create(faces=faces, vertices=vertices, colors=colors)
            # tree_base.units = "m"

            # generate base top
            color = COLOR_TREE_BASE
            vertices = []
            colors = []
            border_pt = {"x": 0.9 / scale_factor, "y": 0}
            steps = 12
            for s in range(steps):
                k = -1 * s / steps
                new_pt = rotate_pt(border_pt, 2 * math.pi * k)
                colors.append(color)
                vertices.extend(
                    [
                        new_pt["x"] + coords["x"],
                        new_pt["y"] + coords["y"],
                        elevation * 1.15,
                    ]
                )
            faces = [steps] + list(range(steps))
            tree_base_top = Mesh.create(faces=faces, vertices=vertices, colors=colors)
            # tree_base_top.units = "m"
    except Exception as e:
        print(e)
        pass

    return [obj, tree_base, tree_base_top]


def road_buffer(poly: Polyline, value: float | int, elevation: float = 0.02) -> Base:
    """Creage a Mesh from Polyline and buffer value."""
    if value is None:
        return
    line = LineString([(p.x, p.y) for p in poly.as_points()])
    area = to_geojson(buffer(line, value, cap_style="square"))  # POLYGON to geojson
    area = json.loads(area)
    vertices = []
    colors = []
    vetricesTuples = []

    color = COLOR_ROAD  # (255<<24) + (150<<16) + (150<<8) + 150 # argb

    for i, c in enumerate(area["coordinates"][0]):
        if i != len(area["coordinates"][0]) - 1:
            vertices.extend(c + [0 + elevation])
            vetricesTuples.append(c)
            colors.append(color)

    face_list = list(range(len(vetricesTuples)))
    face_list, _ = fix_polygon_orientation(vetricesTuples, face_list)
    face_list.reverse()

    mesh = Mesh.create(
        vertices=vertices, colors=colors, faces=[len(vetricesTuples)] + face_list
    )
    # mesh.units = "m"

    return Base(
        # units="m",
        displayValue=[mesh],
        width=2 * value,
        sourceData="© OpenStreetMap",
        sourceUrl="https://www.openstreetmap.org/",
    )
