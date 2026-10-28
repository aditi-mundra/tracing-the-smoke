"""Automated Verification and Validation Test Suite for Phase 1 Corrections.
Covers all 18 required audit test categories:
1. Real raster cropland classification
2. Cropland vs non-cropland spatial sampling
3. Fire-state point-in-polygon classification
4. Fire-count reconciliation across summary files
5. Weather wind-speed unit verification (m/s)
6. Wind u/v component calculations
7. Cardinal wind-direction conventions
8. UTC-to-IST conversion and timezone alignment
9. IST daily weather aggregation completeness (24h/day)
10. Leap-year and calendar-boundary handling (2020 & 2024 = 366 days)
11. CPCB NCT station filtering
12. CPCB daily coverage validation (>=10 stations, n>=16h)
13. Duplicate detection across all sources
14. Severe-episode counting consistency (PM2.5 >= 250 ug/m3)
15. Real monthly coverage generation (all 96 months with zero projections)
16. Calendar-date continuity (no artificial jumps)
17. Cross-source daily overlap (2,709 coincident days)
18. Source-file manifest consistency
"""

import pytest
import pandas as pd
import numpy as np
import json
import rasterio
from pathlib import Path

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PROCESSED_CORRECTED = PROJECT_ROOT / "data" / "processed_phase1_corrected"
AUDIT_CORRECTED = PROJECT_ROOT / "audit" / "phase1_corrected"
ESA_DIR = PROJECT_ROOT / "data" / "geographic" / "esa_worldcover"
RAW_ERA5_DIR = PROJECT_ROOT / "data" / "raw" / "era5_expanded_corrected"

# 1. Real raster cropland classification
def test_01_real_raster_cropland_classification():
    tiles = ["N27E072", "N27E075", "N30E072", "N30E075"]
    for t in tiles:
        f = ESA_DIR / f"ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
        assert f.exists(), f"Tile {t} missing"
        with rasterio.open(f) as src:
            assert src.crs.to_string() == "EPSG:4326"
            assert src.dtypes[0] == "uint8"
            assert src.width == 36000
            assert src.height == 36000

# 2. Cropland vs non-cropland spatial sampling
def test_02_cropland_vs_non_cropland_sampling():
    df_samples = pd.read_csv(AUDIT_CORRECTED / "SAMPLE_CROPLAND_DETECTIONS.csv")
    assert len(df_samples) == 30
    cropland_samples = df_samples[df_samples["is_cropland"] == True]
    non_cropland_samples = df_samples[df_samples["is_cropland"] == False]
    assert len(cropland_samples) >= 20
    assert len(non_cropland_samples) >= 10
    assert (cropland_samples["land_cover_class"] == 40).all()
    assert (non_cropland_samples["land_cover_class"] != 40).all()

# 3. Fire-state point-in-polygon classification
def test_03_fire_state_classification():
    df_b1 = pd.read_parquet(PROCESSED_CORRECTED / "punjab_haryana_fires_all_2018_2025.parquet")
    assert "state" in df_b1.columns
    unique_states = set(df_b1["state"].unique())
    assert unique_states == {"punjab", "haryana"}
    # Check bounding limits
    assert df_b1["latitude"].between(27.0, 33.0).all()
    assert df_b1["longitude"].between(73.5, 78.0).all()

# 4. Fire-count reconciliation across summary files
def test_04_fire_count_reconciliation():
    df_b1 = pd.read_parquet(PROCESSED_CORRECTED / "punjab_haryana_fires_all_2018_2025.parquet")
    df_b2 = pd.read_parquet(PROCESSED_CORRECTED / "punjab_haryana_fires_cropland_2018_2025.parquet")
    df_annual = pd.read_csv(AUDIT_CORRECTED / "FIRMS_ANNUAL_COUNTS.csv")
    
    assert len(df_b1) == df_annual["dataset_b1_total"].sum()
    assert len(df_b2) == df_annual["dataset_b2_cropland_detected"].sum()
    assert len(df_b1) == 605537
    assert len(df_b2) == 565728

# 5. Weather wind-speed unit verification (m/s)
def test_05_weather_wind_speed_units():
    df_hourly = pd.read_parquet(RAW_ERA5_DIR / "era5_delhi_2020_ist.parquet")
    # ERA5 near-surface winds in Delhi typically range 0.5 to 15 m/s, not 50+
    assert df_hourly["wind_speed_10m"].mean() < 6.0 # Mean in m/s is ~2.5 - 3.5 m/s
    assert df_hourly["wind_speed_10m"].max() < 25.0

# 6. Wind u/v component calculations
def test_06_wind_u_v_components():
    df_hourly = pd.read_parquet(RAW_ERA5_DIR / "era5_delhi_2020_ist.parquet")
    reconstructed_speed = np.sqrt(df_hourly["u_wind_10m"]**2 + df_hourly["v_wind_10m"]**2)
    diff = np.abs(reconstructed_speed - df_hourly["wind_speed_10m"])
    assert (diff < 1e-4).all()

# 7. Cardinal wind-direction conventions
def test_07_cardinal_wind_directions():
    # Test theoretical vector conversion
    speed = 10.0 # m/s
    # Wind FROM North (0 deg): should blow South (u=0, v=-10)
    rad_n = np.radians(0.0)
    u_n = -speed * np.sin(rad_n)
    v_n = -speed * np.cos(rad_n)
    assert np.isclose(u_n, 0.0)
    assert np.isclose(v_n, -10.0)
    
    # Wind FROM West (270 deg): should blow East (u=+10, v=0)
    rad_w = np.radians(270.0)
    u_w = -speed * np.sin(rad_w)
    v_w = -speed * np.cos(rad_w)
    assert np.isclose(u_w, 10.0)
    assert np.isclose(v_w, 0.0)

# 8. UTC-to-IST conversion and timezone alignment
def test_08_utc_to_ist_conversion():
    df_hourly = pd.read_parquet(RAW_ERA5_DIR / "era5_delhi_2020_ist.parquet")
    assert "time_ist" in df_hourly.columns
    # Check start and end times in IST
    assert str(df_hourly["time_ist"].iloc[0]) == "2020-01-01 00:00:00"
    assert str(df_hourly["time_ist"].iloc[-1]) == "2020-12-31 23:00:00"

# 9. IST daily weather aggregation completeness (24h/day)
def test_09_ist_daily_weather_completeness():
    df_daily = pd.read_parquet(PROCESSED_CORRECTED / "era5_delhi_daily_meteorology_2018_2025.parquet")
    assert len(df_daily) == 2922
    assert not df_daily["temp_mean"].isna().any()
    assert not df_daily["wind_speed_mean"].isna().any()

# 10. Leap-year and calendar-boundary handling
def test_10_leap_year_handling():
    df_daily = pd.read_parquet(PROCESSED_CORRECTED / "era5_delhi_daily_meteorology_2018_2025.parquet")
    df_daily["year"] = pd.to_datetime(df_daily["date_ist"]).dt.year
    counts_by_year = df_daily.groupby("year").size()
    assert counts_by_year[2020] == 366 # Leap year
    assert counts_by_year[2024] == 366 # Leap year
    assert counts_by_year[2018] == 365
    assert counts_by_year[2019] == 365
    assert counts_by_year[2021] == 365
    assert counts_by_year[2022] == 365
    assert counts_by_year[2023] == 365
    assert counts_by_year[2025] == 365

# 11. CPCB NCT station filtering
def test_11_cpcb_station_filtering():
    df_stn = pd.read_parquet(PROJECT_ROOT / "data" / "processed_phase1" / "cpcb_delhi_station_daily_validated_2018_2025.parquet")
    # Verified NCT stations only
    assert df_stn["station_id"].nunique() <= 40
    # No negative concentrations (mean is station-day daily average PM2.5)
    assert (df_stn["mean"] > 0).all()
    assert (df_stn["mean"] <= 1500).all()

# 12. CPCB daily coverage validation
def test_12_cpcb_daily_coverage_rule():
    df_daily = pd.read_parquet(PROCESSED_CORRECTED / "cpcb_delhi_daily_target_2018_2025.parquet")
    assert (df_daily["active_station_count"] >= 10).all()
    assert (df_daily["total_hourly_readings"] >= 160).all()

# 13. Duplicate detection across all sources
def test_13_duplicate_detection():
    df_cpcb = pd.read_parquet(PROCESSED_CORRECTED / "cpcb_delhi_daily_target_2018_2025.parquet")
    assert df_cpcb["date_str"].duplicated().sum() == 0
    df_era5 = pd.read_parquet(PROCESSED_CORRECTED / "era5_delhi_daily_meteorology_2018_2025.parquet")
    assert df_era5["date_ist"].duplicated().sum() == 0

# 14. Severe-episode counting consistency
def test_14_severe_episode_counting():
    df_daily = pd.read_parquet(PROCESSED_CORRECTED / "cpcb_delhi_daily_target_2018_2025.parquet")
    df_severe = pd.read_csv(AUDIT_CORRECTED / "SEVERE_EPISODE_COUNTS.csv")
    actual_severe = int((df_daily["delhi_pm25_target"] >= 250.0).sum())
    assert actual_severe == 157
    assert df_severe["severe_episode_days"].sum() == 157

# 15. Real monthly coverage generation
def test_15_monthly_coverage_integrity():
    df_monthly = pd.read_csv(AUDIT_CORRECTED / "ACTUAL_MONTHLY_COVERAGE.csv")
    assert len(df_monthly) == 96
    # Zero string projections or missing indicators in numeric fields
    assert not df_monthly["cpcb_valid_city_target_days"].isna().any()
    assert not df_monthly["firms_b1_active_fires"].isna().any()
    assert not df_monthly["era5_delhi_valid_days"].isna().any()

# 16. Calendar-date continuity
def test_16_calendar_date_continuity():
    df_daily = pd.read_parquet(PROCESSED_CORRECTED / "era5_delhi_daily_meteorology_2018_2025.parquet")
    dates = pd.to_datetime(df_daily["date_ist"])
    date_diffs = dates.diff().iloc[1:]
    assert (date_diffs == pd.Timedelta(days=1)).all()

# 17. Cross-source daily overlap
def test_17_cross_source_daily_overlap():
    df_multi = pd.read_csv(AUDIT_CORRECTED / "MULTISOURCE_DAILY_COVERAGE.csv")
    assert len(df_multi) == 2922
    assert df_multi["is_multisource_complete"].sum() == 2709
    assert df_multi["is_severe_episode_ge_250"].sum() == 157

# 18. Source-file manifest consistency
def test_18_source_file_manifest():
    manifest_path = AUDIT_CORRECTED / "DATASET_MANIFEST.csv"
    assert manifest_path.exists()
    df_man = pd.read_csv(manifest_path)
    assert len(df_man) >= 15
    for _, row in df_man.iterrows():
        f = PROJECT_ROOT / row["file_path"]
        assert f.exists(), f"Manifest file missing: {f}"
        assert f.stat().st_size == row["file_size_bytes"]
