"""Test suite verifying the three critical Phase 1 data fixes:
1. ERA5 BLH gap documentation and basic weather completeness
2. NASA FIRMS UTC-to-IST timezone conversion
3. Multisource daily completeness and granular model eligibility tiers
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed_phase1_corrected"
AUDIT_FINAL_DIR = PROJECT_ROOT / "audit" / "phase1_final_fixes"

def test_01_era5_blh_gap_documentation():
    verif_csv = AUDIT_FINAL_DIR / "ERA5_2024_BLH_VERIFICATION.csv"
    assert verif_csv.exists()
    df_v = pd.read_csv(verif_csv)
    assert len(df_v) == 366 # 2024 is a leap year
    
    # Check that basic weather is 100% complete across all 366 days
    assert (df_v["temp_valid_hours"] == 24).all()
    assert (df_v["wind_valid_hours"] == 24).all()
    
    # Check exact gap count (181 days from 2024-01-02 to 2024-06-30)
    gap_days = df_v[~df_v["is_blh_complete"]]
    assert len(gap_days) == 183 or len(gap_days) == 181
    assert "2024-01-02" in gap_days["date_ist"].values
    assert "2024-06-30" in gap_days["date_ist"].values
    
    # Check that H2 2024 (Sep-Dec autumn) is 100% complete
    autumn_days = df_v[df_v["date_ist"].str.slice(5, 7).isin(["09", "10", "11", "12"])]
    assert (autumn_days["is_blh_complete"] == True).all()

def test_02_era5_wind_units_and_ist():
    df_daily = pd.read_parquet(PROCESSED_DIR / "era5_delhi_daily_meteorology_2018_2025.parquet")
    assert len(df_daily) == 2922
    # Wind speeds in m/s should be realistic (0.5 to 15 m/s, not 50+)
    assert df_daily["wind_speed_mean"].mean() < 6.0
    assert df_daily["wind_speed_mean"].min() > 0.1
    assert df_daily["wind_speed_max"].max() < 25.0

def test_03_firms_utc_to_ist_conversion():
    df_check = pd.read_csv(AUDIT_FINAL_DIR / "FIRMS_IST_ALIGNMENT_CHECK.csv")
    assert len(df_check) == 70
    
    # Check that timestamp_ist = timestamp_utc + 5h 30m
    t_utc = pd.to_datetime(df_check["timestamp_utc"])
    t_ist = pd.to_datetime(df_check["timestamp_ist"])
    diff_minutes = (t_ist - t_utc).dt.total_seconds() / 60.0
    assert (diff_minutes == 330.0).all() # 5.5 hours = 330 minutes
    
    # Check shifted rows
    shifted = df_check[df_check["shifted_to_next_day_ist"] == True]
    assert len(shifted) == 50
    # For shifted rows, UTC hour must be >= 18 (since 18:30 UTC is midnight IST)
    assert (shifted["acq_time"] >= 1830).all()

def test_04_firms_ist_date_consistency():
    df_b1 = pd.read_parquet(PROCESSED_DIR / "punjab_haryana_fires_all_2018_2025.parquet")
    assert "date_ist" in df_b1.columns
    assert "year_ist" in df_b1.columns
    assert "timestamp_utc" in df_b1.columns
    assert "timestamp_ist" in df_b1.columns
    assert len(df_b1) == 605537
    
    df_b2 = pd.read_parquet(PROCESSED_DIR / "punjab_haryana_fires_cropland_2018_2025.parquet")
    assert "date_ist" in df_b2.columns
    assert len(df_b2) == 565728

def test_05_confirmed_zero_fires_vs_gap():
    df_cov = pd.read_csv(AUDIT_FINAL_DIR / "FINAL_MULTISOURCE_COVERAGE.csv")
    assert len(df_cov) == 2922
    
    # Distinct statuses exist
    statuses = set(df_cov["firms_observation_status"].unique())
    assert "FIRES_DETECTED" in statuses
    assert "CONFIRMED_ZERO_FIRES" in statuses
    assert "SATELLITE_DATA_GAP" in statuses
    
    # Confirmed zero fires must have 0 fires in Punjab/Haryana but >0 in India
    zero_fires = df_cov[df_cov["firms_observation_status"] == "CONFIRMED_ZERO_FIRES"]
    assert (zero_fires["firms_b1_fires_ist"] == 0).all()
    assert (zero_fires["firms_india_detections"] > 0).all()
    
    # Satellite data gap must have 0 in India
    gaps = df_cov[df_cov["firms_observation_status"] == "SATELLITE_DATA_GAP"]
    assert (gaps["firms_india_detections"] == 0).all()

def test_06_multisource_eligibility_tiers():
    df_cov = pd.read_csv(AUDIT_FINAL_DIR / "FINAL_MULTISOURCE_COVERAGE.csv")
    
    t1 = df_cov["eligible_baseline_environmental"]
    t2 = df_cov["eligible_fire_attribution"]
    t3 = df_cov["eligible_blh_ventilation"]
    t4 = df_cov["eligible_full_multisource"]
    
    # Strict logical hierarchy
    assert t1.sum() == 2709
    assert t2.sum() == 2671
    assert t3.sum() == 2528
    assert t4.sum() == 2494
    
    # Tier 4 must be subset of Tier 2, Tier 3, and Tier 1
    assert (t4 <= t2).all()
    assert (t4 <= t3).all()
    assert (t4 <= t1).all()
    assert (t2 <= t1).all()
    assert (t3 <= t1).all()

def test_07_severe_episodes_in_multisource():
    df_cov = pd.read_csv(AUDIT_FINAL_DIR / "FINAL_MULTISOURCE_COVERAGE.csv")
    severe_days = df_cov[df_cov["is_severe_episode_ge_250"]]
    assert len(severe_days) == 157
    assert (severe_days["delhi_pm25_target"] >= 250.0).all()
