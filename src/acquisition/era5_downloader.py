"""Automated ERA5 Reanalysis Meteorological Downloader.
Acquires hourly ERA5 reanalysis single-level atmospheric variables for Delhi and Punjab-Haryana fire regions.
Includes: 10m wind speed, 10m wind direction, boundary layer height, 2m temperature, 2m dew point,
relative humidity, surface pressure, and derives exact 10m u/v wind vectors.
"""

import logging
import math
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import requests

from backend.app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("era5_downloader")

ERA5_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

class ERA5Downloader:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or settings.DATA_RAW_DIR / "era5"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def fetch_location_hourly(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        location_name: str = "delhi"
    ) -> pd.DataFrame:
        """Fetch hourly ERA5 reanalysis variables for a given geographic point and time period."""
        logger.info(f"Fetching ERA5 reanalysis for {location_name} ({lat:.4f}, {lon:.4f}) from {start_date} to {end_date}...")
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": [
                "temperature_2m",
                "relative_humidity_2m",
                "dew_point_2m",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
                "boundary_layer_height"
            ]
        }
        r = requests.get(ERA5_ARCHIVE_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        hourly = data.get("hourly", {})
        if not hourly or "time" not in hourly:
            logger.warning(f"No hourly data returned for {location_name}")
            return pd.DataFrame()
            
        df = pd.DataFrame(hourly)
        df["time"] = pd.to_datetime(df["time"])
        df["latitude"] = lat
        df["longitude"] = lon
        df["location"] = location_name
        
        # Calculate meteorological u and v components of 10m wind:
        # Meteorological wind direction indicates the direction from which wind blows (0=North, 90=East, 180=South, 270=West).
        # u is eastward velocity (positive towards East), v is northward velocity (positive towards North).
        # When wind blows FROM North (direction=0), it travels South: u=0, v=-speed.
        # When wind blows FROM North-West (direction=315), it travels South-East towards Delhi: u>0, v<0.
        rad = np.radians(df["wind_direction_10m"])
        df["u_wind_10m"] = -df["wind_speed_10m"] * np.sin(rad)
        df["v_wind_10m"] = -df["wind_speed_10m"] * np.cos(rad)
        
        return df

    def download_multi_year(
        self,
        years: List[int],
        locations: Optional[Dict[str, tuple]] = None
    ) -> Path:
        """Download hourly ERA5 weather for Delhi and representative Punjab-Haryana region across study years."""
        if locations is None:
            locations = {
                "delhi": (settings.DELHI_LATITUDE, settings.DELHI_LONGITUDE),
                "punjab_haryana_regional": (30.50, 75.50) # Representative agricultural source region
            }
            
        all_dfs = []
        for year in years:
            start_date = f"{year}-09-01"
            end_date = f"{year}-12-31"
            for loc_name, (lat, lon) in locations.items():
                try:
                    df = self.fetch_location_hourly(lat, lon, start_date, end_date, loc_name)
                    if not df.empty:
                        df["year"] = year
                        all_dfs.append(df)
                except Exception as e:
                    logger.error(f"Error fetching ERA5 for {loc_name} in {year}: {e}")
                    
        if not all_dfs:
            raise RuntimeError("No ERA5 meteorological data could be acquired.")
            
        combined = pd.concat(all_dfs, ignore_index=True)
        out_parquet = self.output_dir / "era5_hourly_2019_2024.parquet"
        combined.to_parquet(out_parquet, index=False)
        combined.to_csv(self.output_dir / "era5_hourly_2019_2024.csv", index=False)
        logger.info(f"Successfully saved {len(combined)} hourly ERA5 meteorological records to {out_parquet}")
        return out_parquet

if __name__ == "__main__":
    downloader = ERA5Downloader()
    downloader.download_multi_year(years=[2019, 2020, 2021, 2022, 2023, 2024])
