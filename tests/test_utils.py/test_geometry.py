"""Unit tests for utils_geometry."""


import math
from utils.utils_geometry import (
    create_flat_mesh,
    create_side_face,
    extrude_building,
    extrude_building_complex,
    extrude_building_simple,
    fix_orientation,
    generate_points_inside_polygon,
    generate_tree,
    join_roads,
    road_buffer,
    rotate_pt,
    split_ways_by_intersection,
    to_triangles,
)

import pytest
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh, Point, Polyline


@pytest.fixture()
def coords() -> list[dict]:
    """Define a clockwise boundary with coordinates."""
    return [
        {"x": 5, "y": 5},
        {"x": 5, "y": -5},
        {"x": -5, "y": -5},
        {"x": -5, "y": 5},
    ]


@pytest.fixture()
def coords_inner() -> list[list[dict]]:
    """Define a list of clockwise voids with coordinates."""
    return [
        [
            {"x": 2, "y": 2},
            {"x": 2, "y": -2},
            {"x": -2, "y": -2},
            {"x": -2, "y": 2},
        ]
    ]


@pytest.fixture()
def point_tuple_list() -> list[tuple]:
    points = [(4, 4), (4, -4), (-4, -4), (-4, 4)]  # clockwise square
    return points


def tests_fix_orientation(point_tuple_list):
    """Unit test for fix_orientation."""
    vert_indices = [0, 1, 2, 3]
    make_clockwise = True
    coef = 1
    new_indices, was_clockwise = fix_orientation(
        point_tuple_list, vert_indices, make_clockwise, coef
    )
    assert new_indices == vert_indices
    assert was_clockwise is True


def tests_fix_orientation_make_clockwise(point_tuple_list):
    """Unit test for fix_orientation enforcing clockwise, down facing orientation."""
    vert_indices = [0, 1, 2, 3]
    make_clockwise = False
    coef = 1
    new_indices, was_clockwise = fix_orientation(
        point_tuple_list, vert_indices, make_clockwise, coef
    )

    vert_indices.reverse()
    assert new_indices == vert_indices
    assert was_clockwise is True


def tests_fix_orientation_coefficient():
    """Unit test for fix_orientation with coefficient skipping the points."""
    point_tuple_list = [
        (4, 4),
        (4, 0),
        (4, -4),
        (0, -4),
        (-4, -4),
        (-4, 0),
        (-4, 4),
        (0, 4),
    ]  # clockwise square
    vert_indices = [0, 1, 2, 3]
    make_clockwise = True
    coef = 2
    new_indices, was_clockwise = fix_orientation(
        point_tuple_list, vert_indices, make_clockwise, coef
    )
    assert new_indices == vert_indices
    assert was_clockwise is True


def tests_create_side_face(coords):
    """Unit test for create_side_face."""
    i = 2
    height = 5
    clockwise_orientation = False
    result = create_side_face(coords, i, height, clockwise_orientation)
    assert isinstance(result, list)
    assert result[8] == result[11] == height


def tests_create_side_face_exception(coords):
    """Unit test for create_side_face."""
    i = len(coords)
    height = 5
    clockwise_orientation = False
    try:
        result = create_side_face(coords, i, height, clockwise_orientation)
        assert False
    except IndexError:
        assert True


def test_to_triangles(coords, coords_inner):
    """Unit test for to_triangles."""
    attempt = 0
    result = to_triangles(coords, coords_inner, attempt)
    assert isinstance(result, tuple)
    assert isinstance(result[0], dict) and isinstance(result[1], int)


def test_to_triangles_invalid_geometry(coords):
    """Unit test for to_triangles with invalid input geometry."""
    coords_inner_wrong = [
        [
            {"x": 20, "y": 20},
            {"x": 20, "y": -20},
            {"x": -20, "y": -20},
            {"x": -20, "y": 20},
        ]
    ]
    attempt = 0
    result = to_triangles(coords, coords_inner_wrong, attempt)
    assert isinstance(result, tuple)
    assert result[0] is None and result[1] is None


def test_rotate_pt():
    """Unit test for rotate_pt."""
    coord = {"x": 5, "y": 0}
    angle_rad = math.pi
    result = rotate_pt(coord, angle_rad)
    assert isinstance(result, dict)
    assert round(result["x"], 6) == -5 and round(result["y"], 6) == 0


def test_create_flat_mesh(coords):
    """Unit test for create_flat_mesh."""
    color = 0
    elevation = 0.01
    result = create_flat_mesh(coords, color, elevation)
    assert isinstance(result, Mesh)
    assert len(result.vertices) == len(coords) * 3


def test_extrude_building_simple(coords):
    """Unit test for extrude_building_simple."""
    height = 10
    result = extrude_building_simple(coords, height)
    assert isinstance(result, Mesh)
    assert len(result.vertices) == 3 * (6 * len(coords))


def test_extrude_building_complex(coords, coords_inner):
    """Unit test for extrude_building_complex."""
    height = 10
    result = extrude_building_complex(coords, coords_inner, height)
    assert isinstance(result, Mesh)
    assert len(result.vertices) >= 3 * (6 * (len(coords) + len(coords_inner)))


def test_extrude_building_no_inner(coords):
    """Unit test for extrude_building."""
    height = 10
    result = extrude_building(coords, [], height)
    assert isinstance(result, Mesh)
    assert len(result.vertices) >= 3 * (6 * len(coords))


def test_extrude_building_with_inner(coords, coords_inner):
    """Unit test for extrude_building."""
    height = 10
    result = extrude_building(coords, coords_inner, height)
    assert isinstance(result, Mesh)
    assert len(result.vertices) >= 3 * (6 * (len(coords) + len(coords_inner)))


def test_road_buffer():
    """Unit test for road_buffer."""
    poly = Polyline.from_points(
        [Point(x=0, y=0, z=0), Point(x=5, y=0, z=0), Point(x=15, y=5, z=0)]
    )
    value = 2.5
    elevation = 0.02
    result = road_buffer(poly, value, elevation)
    assert isinstance(result, Base)


def test_split_ways_by_intersection():
    """Unit test for split_ways_by_intersection."""
    ways = [{"nodes": [0, 1, 2, 3, 1, 4]}, {"nodes": [33, 11, 44]}]
    tags = [{}, {}]
    result = split_ways_by_intersection(ways, tags)
    assert isinstance(result, tuple)
    assert isinstance(result[0], list) and isinstance(result[1], list)
    assert len(result[0]) == len(ways) + 1
    assert result[0][0] == {"nodes": [0, 1, 2, 3]}


def test_join_roads(coords):
    """Unit test for join_roads."""
    closed = True
    result = join_roads(coords, closed)
    assert isinstance(result, Polyline)
    assert result.closed is True


def test_generate_tree():
    """Unit test for generate_tree."""
    tree = {"id": "234"}
    tree_coords = {"x": 10, "y": 20}
    scale_factor = 0.5
    elevation = 0.025
    result = generate_tree(tree, tree_coords, scale_factor, elevation)
    assert isinstance(result, list)
    assert len(result) == 3
    for item in result:
        assert isinstance(item, Mesh)


def test_generate_points_inside_polygon(point_tuple_list):
    """Unit test for generate_points_inside_polygon."""
    point_number = 10
    result = generate_points_inside_polygon(point_tuple_list, point_number)
    assert isinstance(result, list)
    assert len(result) == point_number
    assert isinstance(result[0], tuple)
    assert isinstance(result[0][0], float)
