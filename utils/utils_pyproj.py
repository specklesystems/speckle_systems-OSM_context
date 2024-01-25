from pyproj import CRS, Transformer


def create_custom_crs_string(lat: float, lon: float) -> str:
    """Create Proj4 string for the custom Traverse Mercator projection at lat, lon."""
    new_crs_string = (
        "+proj=tmerc +ellps=WGS84 +datum=WGS84 +units=m +no_defs +lon_0="
        + str(lon)
        + " lat_0="
        + str(lat)
        + " +x_0=0 +y_0=0 +k_0=1"
    )
    return new_crs_string


def create_crs(lat: float, lon: float) -> CRS:
    """Create a projected Coordinate Reference System centered at lat&lon (based on Traverse Mercator)."""
    new_crs_string = create_custom_crs_string(lat, lon)
    crs2 = CRS.from_string(new_crs_string)

    return crs2


def reproject_to_crs(
    lat: float, lon: float, crs_from, crs_to, direction="FORWARD"
) -> tuple[float, float]:
    """Reproject a point to a different Coordinate Reference System."""
    transformer = Transformer.from_crs(crs_from, crs_to, always_xy=True)
    pt: tuple[float, float] = transformer.transform(lon, lat, direction=direction)

    return pt[0], pt[1]


def get_degrees_bbox_from_lat_lon_rad(
    lat: float, lon: float, radius: float | int
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Get min & max values of lat/lon given location and radius."""
    projected_crs = create_crs(lat, lon)
    lon_plus_1, lat_plus_1 = reproject_to_crs(1, 1, projected_crs, "EPSG:4326")
    scale_x_degrees = lon_plus_1 - lon  # degrees in 1m of longitude
    scale_y_degrees = lat_plus_1 - lat  # degrees in 1m of latitude

    min_lat_lon: tuple[float, float] = (
        lat - scale_y_degrees * radius,
        lon - scale_x_degrees * radius,
    )
    max_lat_lon: tuple[float, float] = (
        lat + scale_y_degrees * radius,
        lon + scale_x_degrees * radius,
    )

    return min_lat_lon, max_lat_lon
