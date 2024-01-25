"""Unit tests for utils_pyproj."""
import pyproj
import pytest
from pyproj import CRS

from utils.utils_pyproj import (
    create_crs,
    create_custom_crs_string,
    get_degrees_bbox_from_lat_lon_rad,
    reproject_to_crs,
)


@pytest.fixture()
def crs_from():
    """CRS object in world coordinates."""
    return CRS.from_epsg(4326)


@pytest.fixture()
def crs_to():
    """CRS object from custom coordinates."""
    new_crs_string = create_custom_crs_string(0.1, 51.2)
    return CRS.from_string(new_crs_string)


def test_create_custom_crs_string():
    """Unit test for create_custom_crs_string."""
    lat = 0.1
    lon = 51
    result = create_custom_crs_string(lat, lon)
    assert isinstance(result, str)


def test_create_crs():
    """Unit test for create_crs."""
    lat = 0.1
    lon = 51
    result = create_crs(lat, lon)
    assert isinstance(result, CRS)


def test_create_crs_wrong_inputs():
    """Unit test for create_crs."""
    lat = 220
    lon = 51
    try:
        create_crs(lat, lon)
        assert False
    except pyproj.exceptions.CRSError:
        assert True


def test_reproject_to_crs(crs_from, crs_to):
    """Unit test for reproject_to_crs."""
    lat = 0.1
    lon = 51.2
    result = reproject_to_crs(lat, lon, crs_from, crs_to)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], float) and isinstance(result[1], float)


def test_get_degrees_bbox_from_lat_lon_rad():
    """Unit test for get_degrees_bbox_from_lat_lon_rad."""
    lat = 0.1
    lon = 51.2
    radius = 500
    result = get_degrees_bbox_from_lat_lon_rad(lat, lon, radius)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], tuple) and isinstance(result[1], tuple)
    assert isinstance(result[0][0], float) and isinstance(result[0][1], float)
    assert isinstance(result[1][0], float) and isinstance(result[1][1], float)
