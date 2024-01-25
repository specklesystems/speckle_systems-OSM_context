"""Module with functions using pyproj library.

Used for CRS creation and transformations
"""
from pyproj import CRS, Transformer


def create_custom_crs_string(lat: float, lon: float) -> str:
    """Create Proj4 string for custom Traverse Mercator projection at lat, lon.

    Args:
        lat: latitude in degrees.
        lon: longitude in degrees.

    Returns:
        String representation of a custom CRS in Proj4 standard.
    """
    return (
        "+proj=tmerc +ellps=WGS84 +datum=WGS84 +units=m +no_defs +lon_0="
        + str(lon)
        + " lat_0="
        + str(lat)
        + " +x_0=0 +y_0=0 +k_0=1"
    )


def create_crs(lat: float, lon: float) -> CRS:
    """Create a projected CRS centered at lat&lon (based on Traverse Mercator).

    Args:
        lat: latitude in degrees.
        lon: longitude in degrees.

    Returns:
        Coordinate Reference System as CRS class of pyproj library.
    """
    new_crs_string = create_custom_crs_string(lat, lon)
    return CRS.from_string(new_crs_string)


def reproject_to_crs(
    lat: float,
    lon: float,
    crs_from,
    crs_to,
    direction="FORWARD",
) -> tuple[float, float]:
    """Reproject a point to a different Coordinate Reference System.

    Args:
        lat: latitude.
        lon: longitude.
        crs_from: CRS of the given coordinates (lat, lon).
        crs_to: CRS to transform coordinates to.
        direction: default FORWARD for transforming coordinates from_crs -> to_crs.

    Returns:
        Transformed coordinates in x, y (lon, lat) order.
    """
    transformer = Transformer.from_crs(crs_from, crs_to, always_xy=True)
    pt: tuple[float, float] = transformer.transform(lon, lat, direction=direction)

    return pt[0], pt[1]


def get_degrees_bbox_from_lat_lon_rad(
    lat: float,
    lon: float,
    radius: float | int,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Get min & max values of lat/lon given location and radius.

    Args:
        lat: latitude in degrees.
        lon: longitude in degrees.
        radius: radius in meters.

    Returns:
        2 tuples with min lat& lon, and max lat&lon of the bbox.
    """
    projected_crs = create_crs(lat, lon)
    lon_plus1, lat_plus1 = reproject_to_crs(1, 1, projected_crs, "EPSG:4326")

    min_lat_lon: tuple[float, float] = (
        lat - (lat_plus1 - lat) * radius,
        lon - (lon_plus1 - lon) * radius,
    )
    max_lat_lon: tuple[float, float] = (
        lat + (lat_plus1 - lat) * radius,
        lon + (lon_plus1 - lon) * radius,
    )

    return min_lat_lon, max_lat_lon
