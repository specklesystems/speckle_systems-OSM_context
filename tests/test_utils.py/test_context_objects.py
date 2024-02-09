"""Unit tests for utils_geometry."""

from utils.utils_context_3d_objects import (
    create_flat_mesh,
    extrude_building,
    extrude_building_complex,
    extrude_building_simple,
    generate_tree,
    road_buffer,
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
