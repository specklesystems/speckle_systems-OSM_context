import os
import tempfile
from datetime import datetime

import pytest

from utils.utils_png import (
    add_copyright_text,
    add_scale_bar,
    add_scale_text,
    create_image_from_bbox,
    get_colors_of_points_from_tiles,
    get_image_pixel_color,
    write_png,
)


@pytest.fixture
def temp_folder_path() -> str:
    """Create a folder in TEMP to write tests outputs."""
    folder_name = "png_testing_" + str(datetime.now().timestamp())[:6]
    path = os.path.join(os.path.abspath(tempfile.gettempdir()), folder_name)
    folder_exist = os.path.exists(path)
    if not folder_exist:
        os.makedirs(path)
    return path


def test_write_png(temp_folder_path):
    """Unit test for write_png."""
    color_rows = [
        [0, 0, 0, 255, 255, 255],
        [155, 155, 155, 112, 112, 112],
    ]  # [row1], [row2] etc.
    file_path = os.path.join(temp_folder_path, "image.png")
    write_png(color_rows, file_path)
    assert os.path.exists(file_path)


def test_get_colors_of_points_from_tiles(temp_folder_path):
    """Unit test for get_colors_of_points_from_tiles."""
    min_lat_lon = (59.926754831277286, 10.754621681479746)
    max_lat_lon = (59.92747305777346, 10.755946479246836)
    radius = 30
    png_name = "png_name.png"
    x_px = 256
    y_px = 256
    result = get_colors_of_points_from_tiles(
        min_lat_lon, max_lat_lon, radius, temp_folder_path, png_name, x_px, y_px
    )
    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], list)
    assert len(result[0]) > 0
    assert isinstance(result[0][0], int)


def test_get_image_pixel_color():
    """Unit test for get_image_pixel_color."""
    sizeX = 256
    sizeY = 256
    pixels = list(range(sizeX * sizeY))
    metadata = {"palette": [(0, 0, 0) for p in pixels]}
    x_ratio = 0.1
    y_ratio = 0.1
    average_px_offset = 1
    contrast_factor = 2
    result = get_image_pixel_color(
        sizeX,
        sizeY,
        pixels,
        metadata,
        x_ratio,
        y_ratio,
        average_px_offset,
        contrast_factor,
    )
    assert isinstance(result, tuple)
    assert len(result) == 3
    for r in result:
        assert r == 0


def test_get_image_pixel_color_no_palette():
    """Unit test for get_image_pixel_color."""
    sizeX = 256
    sizeY = 256
    pixels = [0 for _ in range(sizeX * sizeY * 4)]
    metadata = {"alpha": True}
    x_ratio = 0.9
    y_ratio = 0.9
    average_px_offset = 1
    contrast_factor = 2
    result = get_image_pixel_color(
        sizeX,
        sizeY,
        pixels,
        metadata,
        x_ratio,
        y_ratio,
        average_px_offset,
        contrast_factor,
    )
    assert isinstance(result, tuple)
    assert len(result) == 3
    for r in result:
        assert r == 0


def test_get_image_pixel_color_no_palette_no_alpha():
    """Unit test for get_image_pixel_color."""
    sizeX = 256
    sizeY = 256
    pixels = [0 for _ in range(sizeX * sizeY * 3)]
    metadata = {}
    x_ratio = 0.9
    y_ratio = 0.9
    average_px_offset = 1
    contrast_factor = 2
    result = get_image_pixel_color(
        sizeX,
        sizeY,
        pixels,
        metadata,
        x_ratio,
        y_ratio,
        average_px_offset,
        contrast_factor,
    )
    assert isinstance(result, tuple)
    assert len(result) == 3
    for r in result:
        assert r == 0


@pytest.fixture()
def color_rows() -> list[list[int]]:
    """List of rgb colors in rows: 1 sub-list per row."""
    return [[150 for _ in range(256 * 3)] for _ in range(256 * 3)]


def test_add_scale_bar(color_rows):
    """Unit test for add_scale_bar."""
    pixels_per_meter = 5
    scale_meters = 10
    size = 256
    result = add_scale_bar(color_rows, pixels_per_meter, scale_meters, size)
    assert isinstance(result, list)
    assert isinstance(result[0], list)
    assert isinstance(result[0][0], int)


def test_add_scale_text(color_rows):
    """Unit test for add_scale_text."""
    scale_meters = 10
    size = 256
    result = add_scale_text(color_rows, scale_meters, size)
    assert isinstance(result, list)
    assert isinstance(result[0], list)
    assert isinstance(result[0][0], int)


def test_add_copyright_text(color_rows):
    """Unit test for add_copyright_text."""
    size = 256
    result = add_copyright_text(color_rows, size)
    assert isinstance(result, list)
    assert isinstance(result[0], list)
    assert isinstance(result[0][0], int)


def test_create_image_from_bbox():
    """Unit test for create_image_from_bbox."""
    lat = 59.92747305777346
    lon = 10.755946479246836
    radius = 40
    result = create_image_from_bbox((lat, lon), radius)

    custom_temp_folder = "automate_tiles_" + str(datetime.now().timestamp())[:6]
    custom_temp_folder_path = os.path.join(
        os.path.abspath(tempfile.gettempdir()), custom_temp_folder
    )

    png_name = f"map_{int(lat*1000000)}_{int(lon*1000000)}_{radius}.png"
    file_name = os.path.join(custom_temp_folder_path, png_name)

    assert isinstance(result, str)
    assert os.path.exists(custom_temp_folder_path)
    assert os.path.exists(file_name)
