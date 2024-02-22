"""Unit tests for utils_geometry."""

import math

import pytest
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh, Point, Polyline

from utils.utils_geometry import (
    create_side_face,
    fix_polygon_orientation,
    generate_points_inside_polygon,
    join_roads,
    rotate_pt,
    split_ways_by_intersection,
    to_triangles,
)


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
def point_tuple_list() -> list[tuple[int | float, int | float]]:
    points = [(4, 4), (4, -4), (-4, -4), (-4, 4)]  # clockwise square
    return points


def tests_fix_polygon_orientation(point_tuple_list):
    """Unit test for fix_polygon_orientation."""
    vert_indices = [0, 1, 2, 3]
    make_clockwise = True
    coef = 1
    new_indices, was_clockwise = fix_polygon_orientation(
        point_tuple_list, vert_indices, make_clockwise, coef
    )
    assert new_indices == vert_indices
    assert was_clockwise is True


def tests_fix_polygon_orientation_make_clockwise(point_tuple_list):
    """Unit test for fix_polygon_orientation enforcing clockwise, down facing orientation."""
    vert_indices = [0, 1, 2, 3]
    make_clockwise = False
    coef = 1
    new_indices, was_clockwise = fix_polygon_orientation(
        point_tuple_list, vert_indices, make_clockwise, coef
    )

    vert_indices.reverse()
    assert new_indices == vert_indices
    assert was_clockwise is True


def tests_fix_polygon_orientation_coefficient():
    """Unit test for fix_polygon_orientation with coefficient skipping the points."""
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
    new_indices, was_clockwise = fix_polygon_orientation(
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


def test_generate_points_inside_polygon(point_tuple_list):
    """Unit test for generate_points_inside_polygon."""
    point_number = 10
    result = generate_points_inside_polygon(point_tuple_list, point_number)
    assert isinstance(result, list)
    assert len(result) == point_number
    assert isinstance(result[0], tuple)
    assert isinstance(result[0][0], float)
