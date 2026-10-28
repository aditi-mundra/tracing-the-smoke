"""Acquisition and Quality Validation of CPCB Delhi PM2.5 Data (2018 - 2025).
Downloads daily station measurements from XKDR / CPCB API for all available months (2018-01 through 2025-08).
Performs:
1. Spatial verification of station coordinates against authoritative Delhi NCT polygon.
2. Filtering of invalid / zero / negative PM2.5 values.
3. Verification of station-hour count ('n' parameter per station-day).
4. Calculation of daily station-level and Delhi-wide PM2.5 target with minimum station coverage rule.
5. Saves raw and validated processed datasets.
"""

from pathlib import Path
import json
import time
import requests
import pandas as pd
import numpy as np
from shapely.geometry import shape, Point

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "cpcb_expanded"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed_phase1"
GEO_DIR = PROJECT_ROOT / "data" / "geographic"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

XKDR_BASE_URL = "https://airquality.xkdr.org/v1"
DEMO_BEARER = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"
HEADERS = {
    "Authorization": f"Bearer {DEMO_BEARER}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def load_delhi_boundary():
    boundary_file = GEO_DIR / "delhi_nct_boundary.geojson"
    assert boundary_file.exists(), f"Boundary file missing: {boundary_file}"
    with open(boundary_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return shape(data.get("geometry"))

def acquire_cpcb_data():
    print("=== STARTING CPCB EXPANDED HISTORICAL ACQUISITION (2018 - 2025) ===", flush=True)
    delhi_poly = load_delhi_boundary()
    
    # 1. Fetch Station Registry
    print("Step 1: Fetching station directory and verifying Delhi NCT coordinates...", flush=True)
    r = requests.get(f"{XKDR_BASE_URL}/stations", headers=HEADERS, timeout=20)
    r.raise_for_status()
    all_stations = r.json().get("data", [])
    
    station_meta = {}
    delhi_nct_stations = set()
    ncr_border_stations = set()
    
    for s in all_stations:
        sid = s.get("station_id")
        lat = s.get("latitude")
        lon = s.get("longitude")
        name = s.get("station_name", "")
        city = s.get("city_name", "")
        state = s.get("state_name", "")
        
        has_pm25 = "PM2.5" in s.get("parameters", [])
        
        if lat is not None and lon is not None:
            pt = Point(lon, lat)
            in_delhi_nct = delhi_poly.contains(pt)
            
            # Check if within bounding envelope or NCR
            is_ncr = ("delhi" in city.lower()) or ("delhi" in state.lower()) or ("delhi" in name.lower()) or (28.35 <= lat <= 28.95 and 76.75 <= lon <= 77.45)
            
            if in_delhi_nct:
                delhi_nct_stations.add(sid)
            elif is_ncr:
                ncr_border_stations.add(sid)
                
            station_meta[sid] = {
                "station_id": sid,
                "station_name": name,
                "city": city,
                "state": state,
                "latitude": lat,
                "longitude": lon,
                "in_delhi_nct": in_delhi_nct,
                "has_pm25": has_pm25
            }
            
    print(f"Total national stations: {len(all_stations)}", flush=True)
    print(f"Verified stations strictly inside Delhi NCT boundary: {len(delhi_nct_stations)}", flush=True)
    print(f"Adjacent border NCR stations excluded from Delhi-wide target: {len(ncr_border_stations)}", flush=True)
    
    # Save station verification
    with open(METADATA_DIR / "cpcb_delhi_nct_verified_stations.json", "w", encoding="utf-8") as f:
        json.dump({sid: station_meta[sid] for sid in delhi_nct_stations}, f, indent=2)
        
    # 2. Download Daily Measurements Month by Month (2018-01 through 2025-08)
    print("\nStep 2: Downloading station measurements month-by-month...", flush=True)
    all_raw_dfs = []
    
    # Define year-month sequence
    ym_list = []
    for yr in range(2018, 2026):
        for mo in range(1, 13):
            if yr == 2025 and mo > 8:
                continue # Verified unavailable at source
            ym_list.append((yr, mo))
            
    total_months = len(ym_list)
    acquired_records_count = 0
    
    for idx, (yr, mo) in enumerate(ym_list, 1):
        import calendar
        _, last_day = calendar.monthrange(yr, mo)
        s_date = f"{yr}-{mo:02d}-01"
        e_date = f"{yr}-{mo:02d}-{last_day:02d}"
        
        # Save monthly raw JSON cache to allow resumption
        raw_cache_file = RAW_DIR / f"cpcb_delhi_{yr}_{mo:02d}.json"
        
        if raw_cache_file.exists():
            with open(raw_cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            df_m = pd.DataFrame(data)
            all_raw_dfs.append(df_m)
            acquired_records_count += len(df_m)
            print(f"  [{idx}/{total_months}] {yr}-{mo:02d}: Loaded from cache ({len(df_m)} records)", flush=True)
            continue
            
        url = f"{XKDR_BASE_URL}/measurements?city=Delhi&parameter=PM2.5&start={s_date}&end={e_date}&agg=daily&format=json"
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                data = r.json().get("data", [])
                with open(raw_cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                df_m = pd.DataFrame(data)
                if not df_m.empty:
                    all_raw_dfs.append(df_m)
                    acquired_records_count += len(df_m)
                print(f"  [{idx}/{total_months}] {yr}-{mo:02d}: Downloaded {len(df_m)} station records (HTTP 200)", flush=True)
            else:
                print(f"  [{idx}/{total_months}] {yr}-{mo:02d}: HTTP {r.status_code}", flush=True)
        except Exception as e:
            print(f"  [{idx}/{total_months}] {yr}-{mo:02d}: Error {e}", flush=True)
            
        time.sleep(0.15) # Gentle request throttling
        
    print(f"\nTotal raw station-day records acquired: {acquired_records_count:,}", flush=True)
    if not all_raw_dfs:
        raise RuntimeError("Failed to acquire CPCB records!")
        
    combined_raw = pd.concat(all_raw_dfs, ignore_index=True)
    
    # Save combined expanded raw parquet
    combined_raw.to_parquet(RAW_DIR / "delhi_cpcb_pm25_expanded_raw.parquet", index=False)
    print(f"Saved raw dataset to {RAW_DIR / 'delhi_cpcb_pm25_expanded_raw.parquet'}", flush=True)
    
    # 3. Data Cleaning and Validation
    print("\nStep 3: Quality Control & Delhi-Wide Aggregation...", flush=True)
    combined_raw["date_str"] = pd.to_datetime(combined_raw["period_start"]).dt.strftime("%Y-%m-%d")
    combined_raw["date"] = pd.to_datetime(combined_raw["date_str"])
    combined_raw["year"] = combined_raw["date"].dt.year
    combined_raw["month"] = combined_raw["date"].dt.month
    
    # Filter 1: Retain only stations verified strictly inside Delhi NCT
    combined_raw["in_delhi_nct"] = combined_raw["station_id"].isin(delhi_nct_stations)
    nct_obs = combined_raw[combined_raw["in_delhi_nct"]].copy()
    print(f"  Records strictly within Delhi NCT: {len(nct_obs):,} (Excluded {len(combined_raw) - len(nct_obs):,} border NCR records)", flush=True)
    
    # Filter 2: Value validity (PM2.5 > 0 and PM2.5 <= 1500 ug/m3)
    valid_mask = (nct_obs["mean"] > 0) & (nct_obs["mean"] <= 1500) & (nct_obs["mean"].notna())
    valid_obs = nct_obs[valid_mask].copy()
    print(f"  Valid non-negative PM2.5 observations: {len(valid_obs):,} (Excluded {(~valid_mask).sum():,} invalid records)", flush=True)
    
    # Filter 3: Minimum hourly completeness rule
    # In CPCB CAAQM daily aggregates, 'n' is the number of valid hourly measurements in the day.
    # Standard environmental rule: require at least 16 hours of observations (66.7% daily coverage) for station-day validity.
    valid_obs["hourly_completeness_valid"] = valid_obs["n"] >= 16
    high_quality_station_days = valid_obs[valid_obs["hourly_completeness_valid"]].copy()
    print(f"  High-quality station-days (n >= 16 hours): {len(high_quality_station_days):,} ({len(high_quality_station_days)/len(valid_obs)*100:.1f}%)", flush=True)
    
    # Save station-level validated dataset
    high_quality_station_days.to_parquet(PROCESSED_DIR / "cpcb_delhi_station_daily_validated_2018_2025.parquet", index=False)
    
    # 4. Delhi-Wide City Target Aggregation
    # Requirement: At least 10 active NCT stations reporting on a given calendar day for valid citywide target
    citywide_daily = high_quality_station_days.groupby("date_str").agg(
        delhi_pm25_mean=("mean", "mean"),
        delhi_pm25_median=("mean", "median"),
        delhi_pm25_std=("mean", "std"),
        active_station_count=("station_id", "nunique"),
        total_hourly_readings=("n", "sum")
    ).reset_index()
    
    citywide_daily["date"] = pd.to_datetime(citywide_daily["date_str"])
    citywide_daily["year"] = citywide_daily["date"].dt.year
    citywide_daily["month"] = citywide_daily["date"].dt.month
    
    # Minimum citywide station coverage threshold: >= 10 stations
    citywide_daily["is_valid_city_target"] = citywide_daily["active_station_count"] >= 10
    valid_target_days = citywide_daily[citywide_daily["is_valid_city_target"]].copy()
    
    print(f"\n--- CPCB VALIDATION SUMMARY ---", flush=True)
    print(f"Total calendar days with measurements: {len(citywide_daily)}")
    print(f"Valid citywide daily target days (>= 10 NCT stations): {len(valid_target_days)} days", flush=True)
    print(f"Mean reporting stations per day: {valid_target_days['active_station_count'].mean():.1f}", flush=True)
    print(f"Overall Citywide Mean PM2.5: {valid_target_days['delhi_pm25_mean'].mean():.2f} ug/m3", flush=True)
    print(f"Date Range: {valid_target_days['date_str'].min()} to {valid_target_days['date_str'].max()}", flush=True)
    
    # Annual breakdown
    annual_counts = valid_target_days.groupby("year")["date_str"].count().to_dict()
    print(f"Valid daily target days per year: {annual_counts}", flush=True)
    
    # Save final validated daily target
    valid_target_days.to_parquet(PROCESSED_DIR / "cpcb_delhi_daily_target_2018_2025.parquet", index=False)
    valid_target_days.to_csv(PROCESSED_DIR / "cpcb_delhi_daily_target_2018_2025.csv", index=False)
    print(f"Saved validated daily citywide target to {PROCESSED_DIR / 'cpcb_delhi_daily_target_2018_2025.parquet'}", flush=True)

if __name__ == "__main__":
    acquire_cpcb_data()
