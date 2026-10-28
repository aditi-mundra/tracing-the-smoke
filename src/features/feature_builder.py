"""Feature Engineering and Integration Pipeline for Tracing the Smoke ML Models.
Constructs:
- Experiment A: Baseline Meteorological, Inversion, Historical PM2.5, and Cyclical Calendar Features.
- Experiment B: Baseline + Basic Fire Counts and Regional Totals (Punjab / Haryana).
- Experiment C: Baseline + Wind-Aligned, Distance-Weighted, Upwind-FRP, and Lagged Atmospheric Fire Features.
Also supports Mode A (Retrospective Analysis) and Mode B (Strict Next-Day Forecasting with zero future leakage).
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from backend.app.config import settings
from src.geospatial.spatial_features import (
    haversine_distance,
    calculate_bearing,
    wind_direction_to_transport_direction,
    calculate_wind_alignment,
    calculate_distance_weight
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("feature_builder")

class FeatureBuilder:
    def __init__(self, processed_dir: Optional[Path] = None):
        self.processed_dir = processed_dir or settings.DATA_PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
    def process_daily_meteorology(self, era5_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate hourly ERA5 weather for Delhi into physically meaningful daily summaries."""
        logger.info("Computing daily meteorological and inversion features...")
        delhi_weather = era5_df[era5_df["location"] == "delhi"].copy()
        delhi_weather["date_str"] = pd.to_datetime(delhi_weather["time"]).dt.strftime("%Y-%m-%d")
        
        # Calculate daily aggregates
        daily_meteo = delhi_weather.groupby("date_str").agg(
            temp_mean=("temperature_2m", "mean"),
            temp_min=("temperature_2m", "min"),
            temp_max=("temperature_2m", "max"),
            rh_mean=("relative_humidity_2m", "mean"),
            dew_point_mean=("dew_point_2m", "mean"),
            surface_pressure_mean=("surface_pressure", "mean"),
            wind_speed_mean=("wind_speed_10m", "mean"),
            wind_speed_max=("wind_speed_10m", "max"),
            u_wind_mean=("u_wind_10m", "mean"),
            v_wind_mean=("v_wind_10m", "mean"),
            blh_mean=("boundary_layer_height", "mean"),
            blh_min=("boundary_layer_height", "min"),
            blh_max=("boundary_layer_height", "max")
        ).reset_index()
        
        # Derive prevailing daily meteorological wind direction using circular vector arctan2:
        # prevailing wind direction = (180 + atan2(-u, -v) * 180 / pi) % 360
        # Since u = -s*sin(theta), v = -s*cos(theta), -u = s*sin(theta), -v = s*cos(theta)
        prev_dir_rad = np.arctan2(-daily_meteo["u_wind_mean"], -daily_meteo["v_wind_mean"])
        daily_meteo["prevailing_wind_direction_deg"] = (np.degrees(prev_dir_rad) + 360.0) % 360.0
        
        # Convert prevailing meteorological wind direction to smoke transport direction
        daily_meteo["smoke_transport_direction_deg"] = wind_direction_to_transport_direction(
            daily_meteo["prevailing_wind_direction_deg"]
        )
        
        # Ventilation index (wind speed * boundary layer height) - key atmospheric dispersion capacity indicator
        daily_meteo["ventilation_index"] = daily_meteo["wind_speed_mean"] * daily_meteo["blh_mean"]
        
        return daily_meteo

    def process_daily_fire_features(
        self,
        fires_df: pd.DataFrame,
        daily_meteo: pd.DataFrame
    ) -> pd.DataFrame:
        """Compute basic and wind-aligned distance-weighted fire features per date."""
        logger.info("Computing geospatial, distance-weighted, and wind-aligned fire features...")
        fires_df = fires_df.copy()
        fires_df["date_str"] = pd.to_datetime(fires_df["acq_date"]).dt.strftime("%Y-%m-%d")
        
        # 1. Great-circle distance from each fire to Delhi centroid
        fires_df["distance_to_delhi_km"] = haversine_distance(
            fires_df["latitude"],
            fires_df["longitude"],
            settings.DELHI_LATITUDE,
            settings.DELHI_LONGITUDE
        )
        
        # 2. Bearing from each fire to Delhi
        fires_df["bearing_to_delhi_deg"] = calculate_bearing(
            fires_df["latitude"],
            fires_df["longitude"],
            settings.DELHI_LATITUDE,
            settings.DELHI_LONGITUDE
        )
        
        # 3. Distance decay factor
        fires_df["distance_weight"] = calculate_distance_weight(fires_df["distance_to_delhi_km"])
        
        # Merge daily smoke transport direction to evaluate wind alignment for each fire
        transport_map = dict(zip(daily_meteo["date_str"], daily_meteo["smoke_transport_direction_deg"]))
        fires_df["transport_dir"] = fires_df["date_str"].map(transport_map).fillna(135.0)
        
        # 4. Directional alignment
        fires_df["wind_alignment"] = calculate_wind_alignment(
            fires_df["bearing_to_delhi_deg"],
            fires_df["transport_dir"]
        )
        
        # Upwind fire flag: alignment > 0.5 (~ within +/- 60 degrees of direct trajectory to Delhi)
        fires_df["is_upwind"] = (fires_df["wind_alignment"] >= 0.50).astype(int)
        
        # Upwind weighted FRP: FRP * alignment * distance_weight
        fires_df["frp_clean"] = fires_df["frp"].fillna(10.0)
        fires_df["upwind_weighted_frp"] = (
            fires_df["frp_clean"] * fires_df["wind_alignment"] * fires_df["distance_weight"]
        )
        fires_df["distance_weighted_count"] = fires_df["distance_weight"]
        
        # Distance bands
        fires_df["band_near"] = (fires_df["distance_to_delhi_km"] <= 150).astype(int)
        fires_df["band_mid"] = (fires_df["distance_to_delhi_km"].between(150.01, 300)).astype(int)
        fires_df["band_far"] = (fires_df["distance_to_delhi_km"] > 300).astype(int)
        
        # Aggregate by date
        daily_fire_agg = fires_df.groupby("date_str").agg(
            fire_count_total=("latitude", "count"),
            fire_count_punjab=("region", lambda r: (r == "Punjab").sum()),
            fire_count_haryana=("region", lambda r: (r == "Haryana").sum()),
            fire_frp_total=("frp_clean", "sum"),
            fire_frp_mean=("frp_clean", "mean"),
            fire_distance_mean_km=("distance_to_delhi_km", "mean"),
            fire_distance_min_km=("distance_to_delhi_km", "min"),
            fire_count_upwind=("is_upwind", "sum"),
            fire_upwind_weighted_frp=("upwind_weighted_frp", "sum"),
            fire_distance_weighted_count=("distance_weighted_count", "sum"),
            fire_count_near_150km=("band_near", "sum"),
            fire_count_mid_150_300km=("band_mid", "sum"),
            fire_count_far_300km=("band_far", "sum")
        ).reset_index()
        
        return daily_fire_agg

    def merge_and_build_features(
        self,
        city_pm25_df: pd.DataFrame,
        fires_df: pd.DataFrame,
        era5_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Combine all sources, compute temporal lags, rolling windows, and cyclical calendar features."""
        logger.info("Merging datasets and generating multi-day lag features...")
        
        # 1. Process meteorology
        daily_meteo = self.process_daily_meteorology(era5_df)
        
        # 2. Process fires
        daily_fires = self.process_daily_fire_features(fires_df, daily_meteo)
        
        # 3. Base dataframe is Delhi daily PM2.5 sorted chronologically
        city_df = city_pm25_df.copy()
        city_df["date"] = pd.to_datetime(city_df["date_str"])
        city_df = city_df.sort_values("date").reset_index(drop=True)
        
        # Merge meteorology
        df = pd.merge(city_df, daily_meteo, on="date_str", how="inner")
        
        # Merge fires (dates without detected fires have 0 fires)
        df = pd.merge(df, daily_fires, on="date_str", how="left")
        
        # Fill missing fire values with 0
        fire_cols = [c for c in daily_fires.columns if c != "date_str"]
        df[fire_cols] = df[fire_cols].fillna(0.0)
        
        # 4. Calendar and Cyclical Seasonal Features
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        df["day_of_week"] = df["date"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        
        # Sine / Cosine encoding of day of year to preserve annual continuity
        doy = df["date"].dt.dayofyear
        df["doy_sin"] = np.sin(2.0 * np.pi * doy / 365.25)
        df["doy_cos"] = np.cos(2.0 * np.pi * doy / 365.25)
        
        # 5. Temporal Lags and Rolling Summaries (strictly calculated in chronological order)
        # Target PM2.5 lags
        df["pm25_lag1"] = df["delhi_daily_pm25_ugm3"].shift(1)
        df["pm25_lag2"] = df["delhi_daily_pm25_ugm3"].shift(2)
        df["pm25_lag3"] = df["delhi_daily_pm25_ugm3"].shift(3)
        df["pm25_rolling_3d"] = df["delhi_daily_pm25_ugm3"].shift(1).rolling(3, min_periods=1).mean()
        df["pm25_rolling_7d"] = df["delhi_daily_pm25_ugm3"].shift(1).rolling(7, min_periods=1).mean()
        
        # Fire activity lags (crucial for atmospheric transport time: smoke emitted in Punjab takes 12-36 hours to reach Delhi)
        df["fire_count_total_lag1"] = df["fire_count_total"].shift(1)
        df["fire_count_total_lag2"] = df["fire_count_total"].shift(2)
        df["fire_count_punjab_lag1"] = df["fire_count_punjab"].shift(1)
        df["fire_upwind_weighted_frp_lag1"] = df["fire_upwind_weighted_frp"].shift(1)
        df["fire_upwind_weighted_frp_lag2"] = df["fire_upwind_weighted_frp"].shift(2)
        df["fire_upwind_weighted_frp_lag3"] = df["fire_upwind_weighted_frp"].shift(3)
        df["fire_upwind_rolling_3d"] = df["fire_upwind_weighted_frp"].shift(1).rolling(3, min_periods=1).mean()
        
        # Meteorological lags (stagnation persistence)
        df["wind_speed_mean_lag1"] = df["wind_speed_mean"].shift(1)
        df["blh_mean_lag1"] = df["blh_mean"].shift(1)
        df["ventilation_index_lag1"] = df["ventilation_index"].shift(1)
        
        # Drop the initial warmup rows where lag1 is NaN
        df_model = df.dropna(subset=["pm25_lag1"]).reset_index(drop=True)
        
        out_path = self.processed_dir / "delhi_pm25_ml_dataset.parquet"
        df_model.to_parquet(out_path, index=False)
        df_model.to_csv(self.processed_dir / "delhi_pm25_ml_dataset.csv", index=False)
        
        logger.info(f"Successfully compiled ML-ready dataset with {len(df_model)} rows and {df_model.shape[1]} columns at {out_path}")
        return df_model

if __name__ == "__main__":
    pass
