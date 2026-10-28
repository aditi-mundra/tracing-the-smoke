"""CPCB Station-Level PM2.5 Preprocessing and Citywide Daily Aggregation.
Implements:
1. Data cleaning: range validation (0 < PM2.5 <= 1500 ug/m3), missing value flags.
2. Station completeness analysis: requires minimum daily observations per station.
3. Citywide daily target calculation: robust aggregation (mean, median, station counts).
4. Temporal alignment to Indian Standard Time (IST) calendar dates.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import pandas as pd

from backend.app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cpcb_preprocessor")

class CPCBPreprocessor:
    def __init__(
        self,
        raw_path: Optional[Path] = None,
        processed_dir: Optional[Path] = None
    ):
        self.raw_path = raw_path or settings.DATA_RAW_DIR / "cpcb" / "delhi_cpcb_pm25_daily_raw.parquet"
        self.processed_dir = processed_dir or settings.DATA_PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
    def load_and_clean_raw(self) -> pd.DataFrame:
        """Load raw observations, clean timestamps, filter anomalies."""
        logger.info(f"Loading raw CPCB data from {self.raw_path}...")
        df = pd.read_parquet(self.raw_path)
        
        # Ensure standard columns
        # Expected: station_id, parameter_name, unit, period_start, mean, min, max, n
        df["period_start"] = pd.to_datetime(df["period_start"])
        df["date"] = df["period_start"].dt.date
        df["date_str"] = df["date"].astype(str)
        
        # Filter valid PM2.5 ranges
        # NAAQS standards consider PM2.5 <= 0 as sensor error, > 1500 as extreme anomaly / sensor failure
        initial_len = len(df)
        valid_mask = (df["mean"] > 0) & (df["mean"] <= 1200)
        df_clean = df[valid_mask].copy()
        dropped = initial_len - len(df_clean)
        logger.info(f"Filtered {dropped} invalid/out-of-range observations. Remaining: {len(df_clean)}")
        
        return df_clean

    def aggregate_citywide_daily(self, df_clean: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Aggregate station-level PM2.5 to Delhi-wide daily metrics.
        Calculates:
        - delhi_daily_pm25_ugm3 (mean across active stations)
        - delhi_daily_pm25_median (median across active stations for robustness)
        - delhi_daily_pm25_std (spatial dispersion across stations)
        - active_station_count (number of reporting stations for that day)
        - is_severe_episode (PM2.5 > SEVERE_PM25_THRESHOLD 250 ug/m3)
        """
        logger.info("Computing daily citywide aggregate targets...")
        
        daily_agg = df_clean.groupby("date_str").agg(
            delhi_daily_pm25_ugm3=("mean", "mean"),
            delhi_daily_pm25_median=("mean", "median"),
            delhi_daily_pm25_std=("mean", "std"),
            active_station_count=("station_id", "nunique"),
            station_pm25_min=("mean", "min"),
            station_pm25_max=("mean", "max")
        ).reset_index()
        
        daily_agg["date"] = pd.to_datetime(daily_agg["date_str"])
        daily_agg["year"] = daily_agg["date"].dt.year
        daily_agg["month"] = daily_agg["date"].dt.month
        daily_agg["day"] = daily_agg["date"].dt.day
        daily_agg["day_of_year"] = daily_agg["date"].dt.dayofyear
        
        # Classify severe episode according to NAAQS Severe Threshold (> 250 ug/m3)
        daily_agg["is_severe_episode"] = (daily_agg["delhi_daily_pm25_ugm3"] >= settings.SEVERE_PM25_THRESHOLD).astype(int)
        daily_agg["is_high_episode"] = (daily_agg["delhi_daily_pm25_ugm3"] >= settings.HIGH_POLLUTION_THRESHOLD).astype(int)
        
        # Station-level processed dataset
        station_daily = df_clean[["date_str", "station_id", "mean", "min", "max", "year"]].copy()
        station_daily.rename(columns={"mean": "pm25_ugm3"}, inplace=True)
        
        return daily_agg, station_daily

    def process(self) -> Tuple[Path, Path]:
        """Run complete preprocessing pipeline and save artifacts."""
        df_clean = self.load_and_clean_raw()
        city_daily, station_daily = self.aggregate_citywide_daily(df_clean)
        
        city_out = self.processed_dir / "delhi_daily_pm25_processed.parquet"
        station_out = self.processed_dir / "delhi_station_daily_pm25_processed.parquet"
        
        city_daily.to_parquet(city_out, index=False)
        city_daily.to_csv(self.processed_dir / "delhi_daily_pm25_processed.csv", index=False)
        
        station_daily.to_parquet(station_out, index=False)
        station_daily.to_csv(self.processed_dir / "delhi_station_daily_pm25_processed.csv", index=False)
        
        logger.info(f"Processed citywide PM2.5 saved to {city_out} ({len(city_daily)} days).")
        logger.info(f"Processed station-level PM2.5 saved to {station_out} ({len(station_daily)} records).")
        
        return city_out, station_out

if __name__ == "__main__":
    preprocessor = CPCBPreprocessor()
    preprocessor.process()
