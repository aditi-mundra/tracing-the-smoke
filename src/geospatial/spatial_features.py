"""Geospatial and Atmospheric Transport Feature Engineering Module.
Implements:
1. Haversine great-circle distance from fire hotspots to Delhi centroid.
2. Forward geographic bearing from fire origin to Delhi.
3. Meteorological wind direction convention and transport direction transformation.
4. Directional wind-fire alignment heuristic (cosine similarity between transport and target).
5. Distance-decay weighting for atmospheric particulate dispersion.
6. Aggregated upwind fire intensity metrics.
"""

import math
import numpy as np
import pandas as pd
from typing import Tuple, Union

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0

def haversine_distance(
    lat1: Union[float, np.ndarray, pd.Series],
    lon1: Union[float, np.ndarray, pd.Series],
    lat2: float,
    lon2: float
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate the great-circle distance between coordinates in kilometers using the Haversine formula."""
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c

def calculate_bearing(
    lat1: Union[float, np.ndarray, pd.Series],
    lon1: Union[float, np.ndarray, pd.Series],
    lat2: float,
    lon2: float
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate forward azimuth / bearing angle from point 1 (fire origin) to point 2 (target/Delhi) in degrees [0, 360).
    0 = North, 90 = East, 180 = South, 270 = West.
    """
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_lambda = np.radians(lon2 - lon1)

    x = np.sin(delta_lambda) * np.cos(phi2)
    y = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(delta_lambda)
    initial_bearing = np.degrees(np.arctan2(x, y))
    
    # Normalize to [0, 360)
    compass_bearing = (initial_bearing + 360.0) % 360.0
    return compass_bearing

def wind_direction_to_transport_direction(
    wind_direction_deg: Union[float, np.ndarray, pd.Series]
) -> Union[float, np.ndarray, pd.Series]:
    """Convert meteorological wind direction (direction FROM which wind blows)
    to atmospheric transport direction (direction TOWARDS which smoke is carried).
    Example: Wind from 315 deg (North-West) transports smoke towards (315 + 180) % 360 = 135 deg (South-East).
    """
    return (wind_direction_deg + 180.0) % 360.0

def calculate_wind_alignment(
    bearing_fire_to_delhi: Union[float, np.ndarray, pd.Series],
    transport_direction: Union[float, np.ndarray, pd.Series]
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate the cosine alignment between the bearing to Delhi and the smoke transport direction.
    Returns:
    - 1.0 when smoke is transported directly towards Delhi.
    - 0.0 when smoke transport is perpendicular or opposite (truncated at 0 to ignore downwind plumes).
    """
    diff_rad = np.radians(bearing_fire_to_delhi - transport_direction)
    alignment = np.cos(diff_rad)
    # Truncate negative values: plumes travelling away from Delhi contribute zero direct advection
    return np.maximum(0.0, alignment)

def calculate_distance_weight(
    distance_km: Union[float, np.ndarray, pd.Series],
    scale_d0: float = 150.0
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate atmospheric dispersion distance decay factor:
    w(d) = 1 / (1 + (d / d0)^1.5)
    Represents atmospheric dilution and particulate deposition over distance.
    At d = 0 km, weight = 1.0. At d = 150 km, weight = 0.5. At d = 300 km, weight ~ 0.26.
    """
    return 1.0 / (1.0 + (distance_km / scale_d0) ** 1.5)
