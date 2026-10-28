"""Stage B: Build Final Machine Learning Dataset.
Constructs continuous daily ML dataset with:
- Continuous 2,922 calendar days (2018-01-01 to 2025-12-31).
- Date-correct historical pollution features (strictly calendar-indexed, no simple positional shifts across gaps).
- Meteorological features (temperature, humidity, pressure, wind vectors, wind speed m/s, BLH, ventilation index).
- Fire features for B1 (all) and B2 (cropland).
- Atmospheric transport proxies (Haversine distance, bearing to Delhi, wind alignment, distance decay, upwind FRP).
- Temporal fire lags (t-1, t-2, t-3) and trailing 3-day fire activity.
- Seasonal & cyclical calendar features (doy_sin, doy_cos, post-monsoon harvest indicator, rabi indicator).
- Dual prediction targets:
    Mode A (Retrospective diagnostic): delhi_daily_pm25_ugm3 on day t.
    Mode B (Strict next-day forecast): pm25_lead1 on day t+1 (using only info through day t).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import logging
import numpy as np
import pandas as pd

from src.geospatial.spatial_features import (
    haversine_distance,
    calculate_bearing,
    calculate_wind_alignment,
    calculate_distance_weight
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_final_ml_dataset")

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PROCESSED_FINAL = PROJECT_ROOT / "data" / "processed_final"
AUDIT_FINAL = PROJECT_ROOT / "audit" / "final"

DELHI_LAT = 28.6139
DELHI_LON = 77.2090

def build_final_dataset():
    logger.info("=== STAGE B: REBUILDING FINAL MACHINE LEARNING DATASET ===")
    
    # 1. Load Data Quality & Eligibility Base Table
    dq_path = PROCESSED_FINAL / "final_daily_data_quality_table.parquet"
    if not dq_path.exists():
        raise FileNotFoundError(f"Run scripts/build_final_data_quality_table.py first! Missing {dq_path}")
        
    df = pd.read_parquet(dq_path)
    df["date"] = pd.to_datetime(df["date_ist"])
    df = df.sort_values("date").reset_index(drop=True)
    logger.info(f"Loaded base data quality table: {len(df)} calendar days.")

    # 2. Compute Geospatial Fire Transport Features from Raw Detections
    logger.info("Computing geospatial transport features from B1 & B2 fire detections...")
    b1_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "punjab_haryana_fires_all_2018_2025.parquet"
    df_fires = pd.read_parquet(b1_path)
    
    # Vectorized geospatial metrics
    df_fires["distance_to_delhi_km"] = haversine_distance(
        df_fires["latitude"].values, df_fires["longitude"].values, DELHI_LAT, DELHI_LON
    )
    df_fires["bearing_to_delhi_deg"] = calculate_bearing(
        df_fires["latitude"].values, df_fires["longitude"].values, DELHI_LAT, DELHI_LON
    )
    df_fires["distance_weight"] = calculate_distance_weight(df_fires["distance_to_delhi_km"].values)
    
    # Map daily smoke transport direction
    transport_map = dict(zip(df["date_ist"], df["smoke_transport_direction_deg"]))
    df_fires["smoke_transport_dir"] = df_fires["date_ist"].map(transport_map).fillna(135.0)
    
    # Directional alignment: cos(bearing - transport) truncated at 0
    df_fires["wind_alignment"] = calculate_wind_alignment(
        df_fires["bearing_to_delhi_deg"].values, df_fires["smoke_transport_dir"].values
    )
    df_fires["is_upwind"] = (df_fires["wind_alignment"] >= 0.50).astype(int)
    
    # Upwind-weighted FRP = frp * alignment * distance_weight
    frp_clean = df_fires["frp"].fillna(10.0).values
    df_fires["upwind_weighted_frp"] = frp_clean * df_fires["wind_alignment"].values * df_fires["distance_weight"].values
    df_fires["distance_weighted_count"] = df_fires["distance_weight"].values
    
    # Distance bands
    df_fires["band_near_150km"] = (df_fires["distance_to_delhi_km"] <= 150.0).astype(int)
    df_fires["band_mid_150_300km"] = (df_fires["distance_to_delhi_km"].between(150.01, 300.0)).astype(int)
    df_fires["band_far_300km"] = (df_fires["distance_to_delhi_km"] > 300.0).astype(int)
    
    # Aggregate transport metrics per IST date
    fire_trans_agg = df_fires.groupby("date_ist").agg(
        fire_count_upwind=("is_upwind", "sum"),
        fire_upwind_weighted_frp=("upwind_weighted_frp", "sum"),
        fire_distance_weighted_count=("distance_weighted_count", "sum"),
        fire_distance_mean_km=("distance_to_delhi_km", "mean"),
        fire_distance_min_km=("distance_to_delhi_km", "min"),
        fire_count_near_150km=("band_near_150km", "sum"),
        fire_count_mid_150_300km=("band_mid_150_300km", "sum"),
        fire_count_far_300km=("band_far_300km", "sum")
    ).reset_index()

    df = pd.merge(df, fire_trans_agg, on="date_ist", how="left")
    
    # Fill transport fire metrics for days with 0 fires
    for c in ["fire_count_upwind", "fire_upwind_weighted_frp", "fire_distance_weighted_count",
              "fire_count_near_150km", "fire_count_mid_150_300km", "fire_count_far_300km"]:
        df[c] = df[c].fillna(0.0)
        
    df["fire_distance_mean_km"] = df["fire_distance_mean_km"].fillna(250.0)
    df["fire_distance_min_km"] = df["fire_distance_min_km"].fillna(200.0)

    # 3. Rename Fire Columns for clean modeling schema
    df["fire_count_total"] = df["firms_b1_fires_ist"]
    df["fire_count_punjab"] = df["firms_b1_punjab_fires_ist"]
    df["fire_count_haryana"] = df["firms_b1_haryana_fires_ist"]
    df["fire_frp_total"] = df["firms_b1_frp_sum_mw"]
    df["fire_frp_mean"] = df["firms_b1_frp_mean_mw"]
    df["fire_frp_max"] = df["firms_b1_frp_max_mw"]
    df["cropland_fire_count"] = df["firms_b2_cropland_fires_ist"]
    df["cropland_frp_total"] = df["firms_b2_cropland_frp_sum_mw"]

    # 4. Strictly Calendar-Correct Historical Pollution Lags
    # Because df has continuous freq='D' (no missing calendar dates), .shift(k) corresponds exactly to day t - k!
    logger.info("Computing date-correct historical pollution lags and rolling statistics...")
    
    # Clean target series: NaN on days without valid CPCB measurement
    pm25_series = df["delhi_daily_pm25_ugm3"].copy()
    pm25_series[~df["cpcb_valid"]] = np.nan
    
    df["pm25_lag1"] = pm25_series.shift(1)
    df["pm25_lag2"] = pm25_series.shift(2)
    df["pm25_lag3"] = pm25_series.shift(3)
    df["pm25_lag7"] = pm25_series.shift(7)
    
    # Trailing rolling statistics strictly using prior calendar days (shift 1)
    df["pm25_rolling_3d"] = pm25_series.shift(1).rolling(3, min_periods=2).mean()
    df["pm25_rolling_7d"] = pm25_series.shift(1).rolling(7, min_periods=4).mean()
    df["pm25_rolling_14d"] = pm25_series.shift(1).rolling(14, min_periods=7).mean()
    df["pm25_volatility_7d"] = pm25_series.shift(1).rolling(7, min_periods=4).std()

    # 5. Fire Activity Lags (Atmospheric transport takes 12 - 36 hours from Punjab/Haryana)
    logger.info("Computing fire temporal lags (t-1, t-2, t-3)...")
    df["fire_count_total_lag1"] = df["fire_count_total"].shift(1)
    df["fire_count_total_lag2"] = df["fire_count_total"].shift(2)
    df["fire_count_total_lag3"] = df["fire_count_total"].shift(3)
    
    df["fire_count_punjab_lag1"] = df["fire_count_punjab"].shift(1)
    df["cropland_fire_count_lag1"] = df["cropland_fire_count"].shift(1)
    
    df["fire_upwind_weighted_frp_lag1"] = df["fire_upwind_weighted_frp"].shift(1)
    df["fire_upwind_weighted_frp_lag2"] = df["fire_upwind_weighted_frp"].shift(2)
    df["fire_upwind_weighted_frp_lag3"] = df["fire_upwind_weighted_frp"].shift(3)
    
    df["fire_upwind_rolling_3d"] = df["fire_upwind_weighted_frp"].shift(1).rolling(3, min_periods=1).mean()
    df["fire_count_rolling_3d"] = df["fire_count_total"].shift(1).rolling(3, min_periods=1).mean()

    # 6. Meteorological Lags (Stagnation & Atmospheric Inversion Persistence)
    df["wind_speed_mean_lag1"] = df["wind_speed_mean"].shift(1)
    df["temp_mean_lag1"] = df["temp_mean"].shift(1)
    df["blh_mean_lag1"] = df["blh_mean"].shift(1)
    df["ventilation_index_lag1"] = df["ventilation_index"].shift(1)

    # 7. Calendar and Cyclical Seasonal Features
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    
    doy = df["date"].dt.dayofyear
    df["doy_sin"] = np.sin(2.0 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2.0 * np.pi * doy / 365.25)
    
    # Harvest indicators
    df["is_kharif_post_monsoon"] = (df["month"].isin([10, 11])).astype(int)
    df["is_rabi_harvest"] = ((df["month"] == 4) & (df["day"] >= 15) | (df["month"] == 5)).astype(int)

    # 8. Target for Mode B: Strict Next-Day Forecasting (day t+1 target)
    df["pm25_lead1"] = pm25_series.shift(-1)
    df["is_severe_episode_lead1"] = (df["pm25_lead1"] >= 250.0).fillna(False).astype(bool)

    # 9. Save Processed Final Dataset
    out_pq = PROCESSED_FINAL / "delhi_pm25_ml_dataset_final.parquet"
    out_csv = PROCESSED_FINAL / "delhi_pm25_ml_dataset_final.csv"
    
    df.to_parquet(out_pq, index=False)
    df.to_csv(out_csv, index=False)
    logger.info(f"Saved final ML dataset ({len(df)} rows, {df.shape[1]} cols) to {out_pq}")

    # 10. Generate Feature Dictionary
    feature_dict = {
        "dataset_metadata": {
            "total_rows": len(df),
            "date_range": f"{df['date_ist'].min()} to {df['date_ist'].max()}",
            "primary_target_mode_a": "delhi_daily_pm25_ugm3",
            "primary_target_mode_b": "pm25_lead1",
            "severe_threshold_ugm3": 250.0
        },
        "experiments": {
            "exp_a_baseline": {
                "name": "Experiment A (Baseline Meteorology & Historical Pollution)",
                "description": "Baseline models using only historical air quality persistence, core weather, and seasonal features. No fire activity.",
                "features": [
                    "temp_mean", "temp_min", "temp_max", "rh_mean", "dew_point_mean",
                    "surface_pressure_mean", "wind_speed_mean", "wind_speed_max",
                    "u_wind_mean", "v_wind_mean", "prevailing_wind_direction_deg",
                    "month", "doy_sin", "doy_cos", "is_weekend",
                    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
                    "pm25_rolling_3d", "pm25_rolling_7d", "pm25_volatility_7d"
                ]
            },
            "exp_b_basic_fires": {
                "name": "Experiment B (Baseline + Raw Regional Fire Activity)",
                "description": "Exp A features plus unweighted regional fire counts and total Fire Radiative Power (B1 all fires).",
                "features": [
                    "temp_mean", "temp_min", "temp_max", "rh_mean", "dew_point_mean",
                    "surface_pressure_mean", "wind_speed_mean", "wind_speed_max",
                    "u_wind_mean", "v_wind_mean", "prevailing_wind_direction_deg",
                    "month", "doy_sin", "doy_cos", "is_weekend",
                    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
                    "pm25_rolling_3d", "pm25_rolling_7d", "pm25_volatility_7d",
                    "fire_count_total", "fire_count_punjab", "fire_count_haryana",
                    "fire_frp_total", "fire_frp_mean"
                ]
            },
            "exp_c_engineered_fires": {
                "name": "Experiment C (Baseline + Wind-Aligned, Distance-Weighted Fire Transport)",
                "description": "Exp B features plus directionally aligned upwind fire counts, upwind FRP, distance decay, and temporal fire lags (t-1, t-2, t-3).",
                "features": [
                    "temp_mean", "temp_min", "temp_max", "rh_mean", "dew_point_mean",
                    "surface_pressure_mean", "wind_speed_mean", "wind_speed_max",
                    "u_wind_mean", "v_wind_mean", "prevailing_wind_direction_deg",
                    "month", "doy_sin", "doy_cos", "is_weekend", "is_kharif_post_monsoon",
                    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
                    "pm25_rolling_3d", "pm25_rolling_7d", "pm25_volatility_7d",
                    "fire_count_total", "fire_count_punjab", "fire_count_haryana",
                    "fire_count_upwind", "fire_upwind_weighted_frp", "fire_distance_weighted_count",
                    "fire_count_near_150km", "fire_count_mid_150_300km",
                    "fire_count_total_lag1", "fire_count_total_lag2",
                    "fire_upwind_weighted_frp_lag1", "fire_upwind_weighted_frp_lag2",
                    "fire_upwind_rolling_3d", "cropland_fire_count", "cropland_fire_count_lag1"
                ]
            },
            "exp_blh_enhanced": {
                "name": "BLH-Enhanced Comparison (Restricted 24h Complete Dates)",
                "description": "Controlled evaluation of boundary layer height and ventilation index on dates with verified 24h completeness.",
                "features": [
                    "temp_mean", "rh_mean", "surface_pressure_mean", "wind_speed_mean",
                    "u_wind_mean", "v_wind_mean", "prevailing_wind_direction_deg",
                    "blh_mean", "blh_min", "ventilation_index",
                    "month", "doy_sin", "doy_cos",
                    "pm25_lag1", "pm25_lag2", "pm25_rolling_3d",
                    "fire_count_total", "fire_count_upwind", "fire_upwind_weighted_frp",
                    "fire_upwind_weighted_frp_lag1"
                ]
            },
            "mode_b_next_day_forecast": {
                "name": "Mode B: Strict Next-Day Forecasting Model",
                "description": "Predicts PM2.5 for day t+1 using strictly observations available at the close of day t. Zero future lookahead.",
                "features": [
                    "temp_mean", "rh_mean", "surface_pressure_mean", "wind_speed_mean",
                    "u_wind_mean", "v_wind_mean", "prevailing_wind_direction_deg",
                    "month", "doy_sin", "doy_cos", "is_weekend", "is_kharif_post_monsoon",
                    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_rolling_3d", "pm25_rolling_7d",
                    "fire_count_total", "fire_count_upwind", "fire_upwind_weighted_frp",
                    "fire_upwind_weighted_frp_lag1", "fire_upwind_rolling_3d"
                ]
            }
        }
    }
    
    with open(PROCESSED_FINAL / "feature_dictionary.json", "w") as f:
        json.dump(feature_dict, f, indent=2)
    with open(AUDIT_FINAL / "FEATURE_DICTIONARY.json", "w") as f:
        json.dump(feature_dict, f, indent=2)
    logger.info("Saved feature dictionary.")

if __name__ == "__main__":
    build_final_dataset()
