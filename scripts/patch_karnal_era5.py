"""Patch missing Karnal ERA5 files for 2020 and 2021 due to Open-Meteo rate limit."""

from pathlib import Path
import time
import requests
import pandas as pd
import numpy as np

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
RAW_ERA5_DIR = PROJECT_ROOT / "data" / "raw" / "era5_expanded"

ERA5_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def patch_karnal():
    lat, lon = 29.6900, 76.9800
    for yr in [2020, 2021]:
        cache_file = RAW_ERA5_DIR / f"era5_haryana_karnal_{yr}.parquet"
        if cache_file.exists():
            print(f"Already exists: {cache_file.name}")
            continue
        print(f"Fetching Haryana Karnal for {yr}...")
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{yr}-01-01",
            "end_date": f"{yr}-12-31",
            "hourly": [
                "temperature_2m",
                "relative_humidity_2m",
                "dew_point_2m",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "boundary_layer_height"
            ],
            "models": "era5"
        }
        r = requests.get(ERA5_ARCHIVE_URL, params=params, headers=HEADERS, timeout=60)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        df["latitude"] = lat
        df["longitude"] = lon
        df["location"] = "haryana_karnal"
        df["year"] = yr
        
        rad = np.radians(df["wind_direction_10m"])
        df["u_wind_10m"] = -df["wind_speed_10m"] * np.sin(rad)
        df["v_wind_10m"] = -df["wind_speed_10m"] * np.cos(rad)
        df["ventilation_index"] = df["wind_speed_10m"] * df["boundary_layer_height"]
        
        df.to_parquet(cache_file, index=False)
        print(f"Successfully saved {len(df)} hours to {cache_file.name}")
        time.sleep(2.0)
        
    # Re-combine all corridor parquet files
    all_files = list(RAW_ERA5_DIR.glob("era5_*_*.parquet"))
    all_files = [f for f in all_files if f.name != "era5_hourly_corridor_2018_2025.parquet"]
    combined = pd.concat([pd.read_parquet(f) for f in all_files], ignore_index=True)
    combined.to_parquet(RAW_ERA5_DIR / "era5_hourly_corridor_2018_2025.parquet", index=False)
    print(f"Total corridor hourly records after patch: {len(combined):,} (Expected 4 locations * 70,128 hrs = 280,512)")

if __name__ == "__main__":
    patch_karnal()
