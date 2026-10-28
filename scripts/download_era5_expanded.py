"""ECMWF ERA5 Atmospheric Reanalysis Expanded Acquisition (2018 - 2025).
Acquires hourly ERA5 reanalysis single-level atmospheric variables using Open-Meteo Historical Archive API:
- Explicit model selection: models=era5
- Temporal range: 2018-01-01 to 2025-12-31 (8 full years = 2,922 days = 70,128 hours/location)
- Corridor sampling strategy (4 representative spatial nodes):
  1. Delhi Centroid (Receptor city): 28.6139 N, 77.2090 E
  2. Punjab Sangrur / Malwa (Core stubble burning district): 30.2500 N, 75.8400 E
  3. Punjab Amritsar / Majha (Northern harvest corridor): 31.6300 N, 74.8700 E
  4. Haryana Karnal (GT Road transport corridor to Delhi): 29.6900 N, 76.9800 E
- Variables: 10m wind speed, 10m wind direction, boundary layer height, temperature, dew point,
  relative humidity, surface pressure, u/v wind vectors, ventilation index.
- Memory-efficient processing: downloads year-by-year per location and aggregates daily.
"""

from pathlib import Path
import json
import time
import requests
import pandas as pd
import numpy as np

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
RAW_ERA5_DIR = PROJECT_ROOT / "data" / "raw" / "era5_expanded"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed_phase1"

RAW_ERA5_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

ERA5_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

CORRIDOR_NODES = {
    "delhi": (28.6139, 77.2090),
    "punjab_sangrur": (30.2500, 75.8400),
    "punjab_amritsar": (31.6300, 74.8700),
    "haryana_karnal": (29.6900, 76.9800)
}

def download_era5_corridor():
    print("=== STARTING ECMWF ERA5 EXPANDED CORRIDOR ACQUISITION (2018 - 2025) ===", flush=True)
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    
    all_hourly_dfs = []
    
    for yr in years:
        s_date = f"{yr}-01-01"
        e_date = f"{yr}-12-31"
        print(f"\n--- Processing ERA5 Reanalysis for Year {yr} ({s_date} to {e_date}) ---", flush=True)
        
        for loc_id, (lat, lon) in CORRIDOR_NODES.items():
            cache_file = RAW_ERA5_DIR / f"era5_{loc_id}_{yr}.parquet"
            
            if cache_file.exists():
                print(f"  [{loc_id}] Loaded cached Parquet for {yr}", flush=True)
                df_loc = pd.read_parquet(cache_file)
                all_hourly_dfs.append(df_loc)
                continue
                
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": s_date,
                "end_date": e_date,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "dew_point_2m",
                    "surface_pressure",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "boundary_layer_height"
                ],
                "models": "era5" # Explicitly select ERA5 reanalysis
            }
            
            print(f"  [{loc_id}] Fetching {yr} hourly reanalysis ({lat:.4f}, {lon:.4f})...", flush=True)
            try:
                r = requests.get(ERA5_ARCHIVE_URL, params=params, headers=HEADERS, timeout=90)
                r.raise_for_status()
                data = r.json()
                hourly = data.get("hourly", {})
                
                df_loc = pd.DataFrame(hourly)
                df_loc["time"] = pd.to_datetime(df_loc["time"])
                df_loc["latitude"] = lat
                df_loc["longitude"] = lon
                df_loc["location"] = loc_id
                df_loc["year"] = yr
                
                # Derive meteorological u and v wind components
                # u: zonal velocity (+ Eastward), v: meridional velocity (+ Northward)
                rad = np.radians(df_loc["wind_direction_10m"])
                df_loc["u_wind_10m"] = -df_loc["wind_speed_10m"] * np.sin(rad)
                df_loc["v_wind_10m"] = -df_loc["wind_speed_10m"] * np.cos(rad)
                
                # Ventilation index
                df_loc["ventilation_index"] = df_loc["wind_speed_10m"] * df_loc["boundary_layer_height"]
                
                df_loc.to_parquet(cache_file, index=False)
                all_hourly_dfs.append(df_loc)
                print(f"    Saved {len(df_loc)} hourly observations to {cache_file.name}", flush=True)
                
            except Exception as e:
                print(f"    Error fetching ERA5 for {loc_id} {yr}: {e}", flush=True)
                
            time.sleep(0.3) # Respect Open-Meteo API rate limits
            
    if not all_hourly_dfs:
        raise RuntimeError("No ERA5 records acquired!")
        
    combined_hourly = pd.concat(all_hourly_dfs, ignore_index=True)
    out_hourly_path = RAW_ERA5_DIR / "era5_hourly_corridor_2018_2025.parquet"
    combined_hourly.to_parquet(out_hourly_path, index=False)
    print(f"\nSuccessfully compiled {len(combined_hourly):,} hourly ERA5 records across 4 corridor locations to {out_hourly_path}", flush=True)
    
    # 2. Daily Meteorological Feature Aggregation (Focusing on Delhi receptor & Upwind Corridor)
    print("\nStep 2: Aggregating daily meteorological features for Delhi...", flush=True)
    delhi_hourly = combined_hourly[combined_hourly["location"] == "delhi"].copy()
    delhi_hourly["date_str"] = delhi_hourly["time"].dt.strftime("%Y-%m-%d")
    
    daily_delhi_meteo = delhi_hourly.groupby("date_str").agg(
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
    
    # Vector-averaged prevailing wind direction
    prev_dir_rad = np.arctan2(-daily_delhi_meteo["u_wind_mean"], -daily_delhi_meteo["v_wind_mean"])
    daily_delhi_meteo["prevailing_wind_direction_deg"] = (np.degrees(prev_dir_rad) + 360.0) % 360.0
    daily_delhi_meteo["smoke_transport_direction_deg"] = (daily_delhi_meteo["prevailing_wind_direction_deg"] + 180.0) % 360.0
    daily_delhi_meteo["ventilation_index"] = daily_delhi_meteo["wind_speed_mean"] * daily_delhi_meteo["blh_mean"]
    
    out_daily_meteo = PROCESSED_DIR / "era5_delhi_daily_meteorology_2018_2025.parquet"
    daily_delhi_meteo.to_parquet(out_daily_meteo, index=False)
    daily_delhi_meteo.to_csv(PROCESSED_DIR / "era5_delhi_daily_meteorology_2018_2025.csv", index=False)
    print(f"Saved {len(daily_delhi_meteo)} daily meteorological records to {out_daily_meteo}", flush=True)

if __name__ == "__main__":
    download_era5_corridor()
