"""ECMWF ERA5 Meteorological Acquisition and Processing — CORRECTED.
Resolves:
- Issue 2: Explicit wind_speed_unit='ms' (verified against Open-Meteo hourly_units metadata).
  Calculates u = -v_s * sin(theta) and v = -v_s * cos(theta) with verified m/s units.
- Issue 3: Explicit timezone='Asia/Kolkata' (IST, UTC+05:30).
  Ensures hourly records (00:00 to 23:00 IST) strictly align with local Indian calendar dates.
  Zero boundary hour truncation or off-by-one calendar shift.
"""

from pathlib import Path
import json
import time
import requests
import pandas as pd
import numpy as np

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
RAW_ERA5_CORRECTED = PROJECT_ROOT / "data" / "raw" / "era5_expanded_corrected"
PROCESSED_CORRECTED = PROJECT_ROOT / "data" / "processed_phase1_corrected"

RAW_ERA5_CORRECTED.mkdir(parents=True, exist_ok=True)
PROCESSED_CORRECTED.mkdir(parents=True, exist_ok=True)

ERA5_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

CORRIDOR_NODES = {
    "delhi": (28.6139, 77.2090),
    "punjab_sangrur": (30.2500, 75.8400),
    "punjab_amritsar": (31.6300, 74.8700),
    "haryana_karnal": (29.6900, 76.9800)
}

def acquire_and_process_era5():
    print("=== STARTING ERA5 ACQUISITION & PROCESSING (CORRECTED: m/s & Asia/Kolkata) ===", flush=True)
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    all_hourly_dfs = []
    metadata_log = {}
    
    for yr in years:
        s_date = f"{yr}-01-01"
        e_date = f"{yr}-12-31"
        print(f"\n--- Processing ERA5 Reanalysis for Year {yr} ({s_date} to {e_date}) ---", flush=True)
        
        for loc_id, (lat, lon) in CORRIDOR_NODES.items():
            cache_file = RAW_ERA5_CORRECTED / f"era5_{loc_id}_{yr}_ist.parquet"
            
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
                "models": "era5",              # Explicitly select ERA5 reanalysis
                "wind_speed_unit": "ms",        # Explicitly select m/s (Fix for Issue 2)
                "timezone": "Asia/Kolkata"      # Explicitly select IST timezone (Fix for Issue 3)
            }
            
            print(f"  [{loc_id}] Fetching {yr} hourly reanalysis in IST (m/s)...", flush=True)
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    r = requests.get(ERA5_ARCHIVE_URL, params=params, headers=HEADERS, timeout=90)
                    r.raise_for_status()
                    data = r.json()
                    
                    # 1. VERIFY RETURNED UNITS
                    hourly_units = data.get("hourly_units", {})
                    assert hourly_units.get("wind_speed_10m") == "m/s", f"Expected m/s, got {hourly_units.get('wind_speed_10m')}"
                    metadata_log[f"{loc_id}_{yr}"] = hourly_units
                    
                    hourly = data.get("hourly", {})
                    df_loc = pd.DataFrame(hourly)
                    df_loc["time_ist"] = pd.to_datetime(df_loc["time"])
                    df_loc["date_ist"] = df_loc["time_ist"].dt.strftime("%Y-%m-%d")
                    df_loc["latitude"] = lat
                    df_loc["longitude"] = lon
                    df_loc["location"] = loc_id
                    df_loc["year"] = yr
                    
                    # 2. DERIVE METEOROLOGICAL u AND v COMPONENTS (m/s)
                    # theta is direction wind comes FROM (0=N, 90=E, 180=S, 270=W)
                    # u: zonal velocity (+ Eastward) = -v_s * sin(theta)
                    # v: meridional velocity (+ Northward) = -v_s * cos(theta)
                    rad = np.radians(df_loc["wind_direction_10m"])
                    df_loc["u_wind_10m"] = -df_loc["wind_speed_10m"] * np.sin(rad)
                    df_loc["v_wind_10m"] = -df_loc["wind_speed_10m"] * np.cos(rad)
                    
                    # Instantaneous ventilation index (m^2/s)
                    df_loc["ventilation_index"] = df_loc["wind_speed_10m"] * df_loc["boundary_layer_height"]
                    
                    df_loc.to_parquet(cache_file, index=False)
                    all_hourly_dfs.append(df_loc)
                    print(f"    Saved {len(df_loc)} hourly observations to {cache_file.name} (Unit verified: m/s, TZ: IST)", flush=True)
                    break
                except Exception as e:
                    print(f"    Attempt {attempt+1} failed: {e}. Retrying...", flush=True)
                    time.sleep(2.0 * (attempt + 1))
            else:
                raise RuntimeError(f"Failed to fetch ERA5 for {loc_id} {yr}")
                
            time.sleep(1.2) # Throttling for Open-Meteo archive API
            
    # Combine corridor hourly records
    combined_hourly = pd.concat(all_hourly_dfs, ignore_index=True)
    out_corridor_path = RAW_ERA5_CORRECTED / "era5_hourly_corridor_2018_2025_ist.parquet"
    combined_hourly.to_parquet(out_corridor_path, index=False)
    print(f"\nSaved master corridor hourly archive to {out_corridor_path} ({len(combined_hourly):,} records)", flush=True)
    
    # Aggregate Delhi Receptor Daily Summary
    print("\nAggregating Delhi Receptor daily meteorology in Indian Standard Time (IST)...", flush=True)
    delhi_hourly = combined_hourly[combined_hourly["location"] == "delhi"].copy()
    
    # Verify each date has exactly 24 hourly readings
    hrs_per_day = delhi_hourly.groupby("date_ist").size()
    incomplete_days = hrs_per_day[hrs_per_day != 24]
    if len(incomplete_days) > 0:
        print(f"WARNING: Found {len(incomplete_days)} incomplete days: {incomplete_days}")
    else:
        print(f"All {len(hrs_per_day)} calendar days have exactly 24 hourly readings (100% complete)!", flush=True)
        
    daily_delhi_meteo = delhi_hourly.groupby("date_ist").agg(
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
    
    # Meteorological vector average prevailing wind direction
    prev_dir_rad = np.arctan2(-daily_delhi_meteo["u_wind_mean"], -daily_delhi_meteo["v_wind_mean"])
    daily_delhi_meteo["prevailing_wind_direction_deg"] = (np.degrees(prev_dir_rad) + 360.0) % 360.0
    daily_delhi_meteo["smoke_transport_direction_deg"] = (daily_delhi_meteo["prevailing_wind_direction_deg"] + 180.0) % 360.0
    daily_delhi_meteo["ventilation_index"] = daily_delhi_meteo["wind_speed_mean"] * daily_delhi_meteo["blh_mean"]
    
    out_daily_meteo_pq = PROCESSED_CORRECTED / "era5_delhi_daily_meteorology_2018_2025.parquet"
    out_daily_meteo_csv = PROCESSED_CORRECTED / "era5_delhi_daily_meteorology_2018_2025.csv"
    daily_delhi_meteo.to_parquet(out_daily_meteo_pq, index=False)
    daily_delhi_meteo.to_csv(out_daily_meteo_csv, index=False)
    print(f"Saved {len(daily_delhi_meteo)} daily meteorological records to {out_daily_meteo_pq} and .csv", flush=True)

if __name__ == "__main__":
    acquire_and_process_era5()
