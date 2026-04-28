"""
Coordinate conversion utilities for Dutch RD (Rijksdriehoek) and WGS84.

This module provides bidirectional coordinate conversion between:
- EPSG:28992 (Dutch RD New / Rijksdriehoeksstelsel)
- EPSG:4326 (WGS84 latitude/longitude)
"""

from pyproj import Transformer


def rd_to_lat_lon(x: float, y: float) -> tuple[float, float]:
    """
    Convert Dutch RD coordinates to WGS84 latitude/longitude.

    Parameters
    ----------
    x : float
        X coordinate in RD system (meters).
    y : float
        Y coordinate in RD system (meters).

    Returns
    -------
    tuple[float, float]
        (latitude, longitude) in WGS84 decimal degrees.

    Example
    -------
    >>> rd_to_lat_lon(121_500, 487_250)  # Amsterdam Dam Square
    (52.3728, 4.8936)
    """
    if x <= 0:
        raise ValueError(f"RD x coordinate must be positive, got {x}")
    if y <= 0:
        raise ValueError(f"RD y coordinate must be positive, got {y}")

    transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lat, lon


def lat_lon_to_rd(latitude: float, longitude: float) -> tuple[float, float]:
    """
    Convert WGS84 latitude/longitude coordinates to Dutch RD.

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees (WGS84).
    longitude : float
        Longitude in decimal degrees (WGS84).

    Returns
    -------
    tuple[float, float]
        (x, y) coordinates in RD system (meters).

    Example
    -------
    >>> lat_lon_to_rd(52.3728, 4.8936)  # Amsterdam Dam Square
    (121500.0, 487250.0)
    """
    if not -90 <= latitude <= 90:
        raise ValueError(f"latitude must be in range [-90, 90], got {latitude}")
    if not -180 <= longitude <= 180:
        raise ValueError(f"longitude must be in range [-180, 180], got {longitude}")

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
    x, y = transformer.transform(longitude, latitude)
    return x, y
