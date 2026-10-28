"""Unit tests for spatial features and atmospheric transport heuristics."""

import math
import numpy as np
import pytest
from src.geospatial.spatial_features import (
    haversine_distance,
    calculate_bearing,
    wind_direction_to_transport_direction,
    calculate_wind_alignment,
    calculate_distance_weight
)

# Reference coordinates
DELHI_LAT = 28.6139
DELHI_LON = 77.2090
LUDHIANA_LAT = 30.9010
LUDHIANA_LON = 75.8573
AMRITSAR_LAT = 31.6340
AMRITSAR_LON = 74.8723

def test_haversine_distance():
    # Distance between Ludhiana and Delhi is approximately 290 - 320 km
    d = haversine_distance(LUDHIANA_LAT, LUDHIANA_LON, DELHI_LAT, DELHI_LON)
    assert 280.0 <= d <= 330.0, f"Expected distance ~300km, got {d:.2f}"
    
    # Distance to self should be 0
    d_self = haversine_distance(DELHI_LAT, DELHI_LON, DELHI_LAT, DELHI_LON)
    assert np.isclose(d_self, 0.0)

def test_calculate_bearing():
    # Ludhiana is North-West of Delhi, so bearing from Ludhiana TO Delhi should be South-East (~140-160 deg)
    bearing = calculate_bearing(LUDHIANA_LAT, LUDHIANA_LON, DELHI_LAT, DELHI_LON)
    assert 135.0 <= bearing <= 165.0, f"Expected bearing ~150 deg, got {bearing:.2f}"

def test_wind_transport_direction():
    # Wind from North (0 deg) blows towards South (180 deg)
    assert np.isclose(wind_direction_to_transport_direction(0.0), 180.0)
    # Wind from West (270 deg) blows towards East (90 deg)
    assert np.isclose(wind_direction_to_transport_direction(270.0), 90.0)
    # Wind from North-West (315 deg) blows towards South-East (135 deg)
    assert np.isclose(wind_direction_to_transport_direction(315.0), 135.0)

def test_wind_alignment():
    # Bearing to Delhi = 145 deg (SE). Wind transport = 145 deg (SE) -> perfect alignment = 1.0
    align_perfect = calculate_wind_alignment(145.0, 145.0)
    assert np.isclose(align_perfect, 1.0)
    
    # Transport opposite = 325 deg (NW) -> negative cosine clamped to 0.0
    align_opposite = calculate_wind_alignment(145.0, 325.0)
    assert np.isclose(align_opposite, 0.0)
    
    # Transport perpendicular = 235 deg (SW) -> 0.0
    align_perp = calculate_wind_alignment(145.0, 235.0)
    assert np.isclose(align_perp, 0.0, atol=1e-2)

def test_distance_decay_weight():
    # Weight at source (d = 0) is 1.0
    assert np.isclose(calculate_distance_weight(0.0), 1.0)
    # Weight at scale d0 (150 km) is 1 / (1 + 1) = 0.5
    assert np.isclose(calculate_distance_weight(150.0, scale_d0=150.0), 0.5)
    # Weight decreases monotonically with distance
    w100 = calculate_distance_weight(100.0)
    w300 = calculate_distance_weight(300.0)
    w500 = calculate_distance_weight(500.0)
    assert w100 > w300 > w500
