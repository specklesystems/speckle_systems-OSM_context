import pytest
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh
from specklepy.objects.units import Units

from utils.utils_osm import (
    get_base_plane,
    get_buildings,
    get_features_from_osm_server,
    get_nature,
    get_roads,
)


@pytest.fixture
def lat():
    """Random latitude."""
    return 59.92747305777346


@pytest.fixture
def lon():
    """Random longitude."""
    return 10.755946479246836


def test_get_base_plane(lat, lon):
    """Unit test for get_base_plane."""
    radius = 50
    units = Units.m
    result = get_base_plane(lat, lon, radius, units)
    assert isinstance(result, Base)
    assert isinstance(result.displayValue, list)
    assert isinstance(result.displayValue[0], Mesh)


def test_get_features_from_osm_server(lat, lon):
    """Unit test for get_features_from_osm_server."""
    keyword = "building"
    min_lat_lon = (lat - 0.00001, lon - 0.00001)
    max_lat_lon = (lat - 0.00001, lon + 0.00001)
    result = get_features_from_osm_server(keyword, min_lat_lon, max_lat_lon)
    assert isinstance(result, list)
    assert len(result) > 0
    building_found = False
    for item in result:
        if item["type"] == "way":
            building_found = True
            break
    assert building_found


def test_get_buildings(lat, lon):
    """Unit test for get_buildings."""
    radius = 100
    angle_rad = 0
    units = Units.m
    result = get_buildings(lat, lon, radius, angle_rad, units)
    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], Base)
    assert isinstance(result[0].displayValue, list)
    assert isinstance(result[0].displayValue[0], Mesh)
    assert result[0].displayValue[0].units == units.value


def test_get_roads(lat, lon):
    """Unit test for get_roads."""
    radius = 100
    angle_rad = 0
    units = Units.m
    result = get_roads(lat, lon, radius, angle_rad, units)
    assert isinstance(result, tuple)

    assert isinstance(result[0], list)
    assert len(result[0]) > 0
    assert isinstance(result[0][0], Base)
    assert result[0][0].units == units.value

    assert isinstance(result[1], list)
    assert len(result[1]) > 0
    assert isinstance(result[1][0], Base)
    assert isinstance(result[1][0].displayValue, list)
    assert isinstance(result[1][0].displayValue[0], Mesh)
    assert result[1][0].displayValue[0].units == units.value


def test_get_nature(lat, lon):
    """Unit test for get_nature."""
    radius = 100
    angle_rad = 0
    units = Units.m
    result = get_nature(lat, lon, radius, angle_rad, units)
    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], Base)
    assert isinstance(result[0].displayValue, list)

    for item in result:
        props = item.get_dynamic_member_names()
        if "natural" in props and item["natural"] == "tree":
            assert len(item.displayValue) == 3
        else:
            assert len(item.displayValue) == 1

    assert isinstance(result[0].displayValue[0], Mesh)
    assert result[0].displayValue[0].units == units.value
