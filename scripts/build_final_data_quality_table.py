"""Stage A: Final Data Quality and Eligibility Table Builder.
Resolves:
- A1: Boundary Layer Height 24-hour completeness check (flags 181 missing + 2 partial days).
- A2: Definitive B1 (605,537) vs B2 (565,728) cropland fire records.
- A3: Sensor observation quality categories (VALID_SOURCE_COVERAGE, DOCUMENTED_GAP, UNCERTAIN_COVERAGE, ZERO_DETECTIONS_WITH_VALID_COVERAGE).
- A4: Consistent IST calendar days (2018-01-01 to 2025-12-31 = 2,922 days).
- A5: Definitive daily data-quality and eligibility table.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PROCESSED_FINAL = PROJECT_ROOT / "data" / "processed_final"
AUDIT_FINAL = PROJECT_ROOT / "audit" / "final"
PROCESSED_FINAL.mkdir(parents=True, exist_ok=True)
AUDIT_FINAL.mkdir(parents=True, exist_ok=True)

def build_data_quality_table():
    print("=== STAGE A: BUILDING DEFINITIVE DATA QUALITY & ELIGIBILITY TABLE ===", flush=True)

    # 1. Continuous calendar index (2018-01-01 to 2025-12-31)
    all_dates = pd.date_range("2018-01-01", "2025-12-31", freq="D")
    df = pd.DataFrame({"date_ist": all_dates.strftime("%Y-%m-%d")})
    df["date"] = pd.to_datetime(df["date_ist"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    
    # Season classification
    def get_season(m):
        if m in [10, 11]:
            return "Post-Monsoon (Autumn Harvest)"
        elif m in [12, 1, 2]:
            return "Winter"
        elif m in [3, 4, 5]:
            return "Pre-Monsoon / Summer"
        else:
            return "Monsoon"
    df["season"] = df["month"].apply(get_season)

    # 2. CPCB Target PM2.5
    cpcb_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "cpcb_delhi_daily_target_2018_2025.parquet"
    if not cpcb_path.exists():
        cpcb_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "cpcb_delhi_daily_target_2018_2025.csv"
        df_cpcb = pd.read_csv(cpcb_path)
    else:
        df_cpcb = pd.read_parquet(cpcb_path)
        
    df_cpcb["date_ist"] = df_cpcb["date_str"].astype(str)
    cpcb_cols = ["date_ist", "delhi_pm25_target", "delhi_pm25_median", "delhi_pm25_std", "active_station_count", "is_valid_city_target"]
    df = pd.merge(df, df_cpcb[cpcb_cols], on="date_ist", how="left")
    df = df.rename(columns={"delhi_pm25_target": "delhi_daily_pm25_ugm3"})
    df["cpcb_valid"] = df["is_valid_city_target"].fillna(False).astype(bool)
    df["is_severe_episode_ge_250"] = (df["delhi_daily_pm25_ugm3"] >= 250.0).fillna(False).astype(bool)

    # 3. Hourly ERA5 Weather and BLH 24-hour completeness check
    print("Auditing ERA5 hourly records for 24-hour completeness...", flush=True)
    era5_hourly_dfs = []
    for yr in range(2018, 2026):
        h_file = PROJECT_ROOT / "data" / "raw" / "era5_expanded_corrected" / f"era5_delhi_{yr}_ist.parquet"
        if h_file.exists():
            h_df = pd.read_parquet(h_file)
            h_df["date_str"] = pd.to_datetime(h_df["time_ist"]).dt.strftime("%Y-%m-%d")
            era5_hourly_dfs.append(h_df)
            
    df_hourly = pd.concat(era5_hourly_dfs, ignore_index=True)
    
    # Compute hourly completeness per date
    daily_meteo_agg = df_hourly.groupby("date_str").agg(
        hourly_records=("time_ist", "count"),
        blh_valid_hours=("boundary_layer_height", lambda s: s.notna().sum()),
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
    ).reset_index().rename(columns={"date_str": "date_ist"})

    # Strict rule for BLH completeness: exactly 24 valid hourly observations required!
    daily_meteo_agg["blh_complete_24h"] = (daily_meteo_agg["blh_valid_hours"] == 24)
    # If not 24h complete, set BLH aggregates to NaN to avoid partial-day distortion
    mask_incomplete = ~daily_meteo_agg["blh_complete_24h"]
    daily_meteo_agg.loc[mask_incomplete, ["blh_mean", "blh_min", "blh_max"]] = np.nan
    
    # Wind direction & smoke transport
    prev_dir_rad = np.arctan2(-daily_meteo_agg["u_wind_mean"], -daily_meteo_agg["v_wind_mean"])
    daily_meteo_agg["prevailing_wind_direction_deg"] = (np.degrees(prev_dir_rad) + 360.0) % 360.0
    daily_meteo_agg["smoke_transport_direction_deg"] = (daily_meteo_agg["prevailing_wind_direction_deg"] + 180.0) % 360.0
    
    # Ventilation index = wind_speed_mean * blh_mean (NaN if blh is incomplete)
    daily_meteo_agg["ventilation_index"] = daily_meteo_agg["wind_speed_mean"] * daily_meteo_agg["blh_mean"]
    
    # Core weather valid: 24 hourly records of basic meteorology
    daily_meteo_agg["era5_basic_valid"] = (daily_meteo_agg["hourly_records"] == 24) & (daily_meteo_agg["temp_mean"].notna())
    daily_meteo_agg["era5_blh_valid"] = daily_meteo_agg["blh_complete_24h"]

    df = pd.merge(df, daily_meteo_agg, on="date_ist", how="left")

    # 4. NASA FIRMS Fire Activity (B1 all fires, B2 cropland fires)
    print("Auditing NASA FIRMS datasets (B1 & B2)...", flush=True)
    b1_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "punjab_haryana_fires_all_2018_2025.parquet"
    b2_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "punjab_haryana_fires_cropland_2018_2025.parquet"
    df_b1 = pd.read_parquet(b1_path)
    df_b2 = pd.read_parquet(b2_path)
    
    print(f"  Dataset B1 verified count: {len(df_b1):,} detections")
    print(f"  Dataset B2 verified count: {len(df_b2):,} detections (ESA WorldCover Class 40)")
    print(f"  Non-cropland fires: {len(df_b1) - len(df_b2):,} detections")
    
    # Aggregate B1 by date_ist
    b1_daily = df_b1.groupby("date_ist").agg(
        firms_b1_fires_ist=("latitude", "count"),
        firms_b1_punjab_fires_ist=("state", lambda s: (s.str.lower() == "punjab").sum()),
        firms_b1_haryana_fires_ist=("state", lambda s: (s.str.lower() == "haryana").sum()),
        firms_b1_frp_sum_mw=("frp", "sum"),
        firms_b1_frp_mean_mw=("frp", "mean"),
        firms_b1_frp_max_mw=("frp", "max")
    ).reset_index()
    
    # Aggregate B2 by date_ist
    b2_daily = df_b2.groupby("date_ist").agg(
        firms_b2_cropland_fires_ist=("latitude", "count"),
        firms_b2_punjab_cropland_fires_ist=("state", lambda s: (s.str.lower() == "punjab").sum()),
        firms_b2_haryana_cropland_fires_ist=("state", lambda s: (s.str.lower() == "haryana").sum()),
        firms_b2_cropland_frp_sum_mw=("frp", "sum"),
        firms_b2_cropland_frp_mean_mw=("frp", "mean"),
        firms_b2_cropland_frp_max_mw=("frp", "max")
    ).reset_index()

    df = pd.merge(df, b1_daily, on="date_ist", how="left")
    df = pd.merge(df, b2_daily, on="date_ist", how="left")
    
    # Fill fire counts with 0 for merge
    for c in ["firms_b1_fires_ist", "firms_b1_punjab_fires_ist", "firms_b1_haryana_fires_ist",
              "firms_b1_frp_sum_mw", "firms_b1_frp_mean_mw", "firms_b1_frp_max_mw",
              "firms_b2_cropland_fires_ist", "firms_b2_punjab_cropland_fires_ist",
              "firms_b2_haryana_cropland_fires_ist", "firms_b2_cropland_frp_sum_mw",
              "firms_b2_cropland_frp_mean_mw", "firms_b2_cropland_frp_max_mw"]:
        df[c] = df[c].fillna(0.0)

    # 5. Satellite Observation Quality Categorization (A3)
    # Load India-wide detection counts to audit instrument availability
    india_daily_counts = {}
    for yr in range(2018, 2026):
        raw_f = PROJECT_ROOT / "data" / "raw" / "firms_annual" / f"viirs-snpp_{yr}_India.csv"
        if raw_f.exists():
            df_ind = pd.read_csv(raw_f, usecols=["acq_date", "acq_time"])
            # Approximate IST date for India count
            df_ind["timestamp_utc"] = pd.to_datetime(df_ind["acq_date"] + " " + df_ind["acq_time"].astype(str).str.zfill(4))
            df_ind["date_ist"] = (df_ind["timestamp_utc"] + pd.Timedelta(hours=5, minutes=30)).dt.strftime("%Y-%m-%d")
            c_ind = df_ind["date_ist"].value_counts().to_dict()
            for d_str, cnt in c_ind.items():
                india_daily_counts[d_str] = india_daily_counts.get(d_str, 0) + cnt

    df["firms_india_detections"] = df["date_ist"].map(india_daily_counts).fillna(0).astype(int)

    # Documented S-NPP anomaly dates:
    # 1. 2022-07-26 to 2022-08-11: S-NPP spacecraft anomaly safe-mode
    # 2. 2024-11-20 to 2024-11-22: S-NPP telemetry loss / star tracker calibration
    documented_gap_dates = set(pd.date_range("2022-07-26", "2022-08-11").strftime("%Y-%m-%d"))
    documented_gap_dates.update(["2024-11-20", "2024-11-21", "2024-11-22"])

    def assign_satellite_quality(row):
        d_str = row["date_ist"]
        m = row["month"]
        b1_cnt = row["firms_b1_fires_ist"]
        ind_cnt = row["firms_india_detections"]
        
        if d_str in documented_gap_dates or ind_cnt == 0:
            return "DOCUMENTED_GAP"
        elif b1_cnt > 0:
            return "VALID_SOURCE_COVERAGE"
        elif m in [6, 7, 8]: # Monsoon heavy cloud obscuration
            return "UNCERTAIN_COVERAGE"
        else:
            return "ZERO_DETECTIONS_WITH_VALID_COVERAGE"

    df["satellite_observation_quality"] = df.apply(assign_satellite_quality, axis=1)
    df["firms_valid"] = df["satellite_observation_quality"].isin([
        "VALID_SOURCE_COVERAGE", "ZERO_DETECTIONS_WITH_VALID_COVERAGE"
    ])

    # 6. Model Eligibility Flags
    # Tier 1: Baseline Environmental (Delhi PM2.5 + Core Weather)
    df["eligible_baseline_environmental"] = df["cpcb_valid"] & df["era5_basic_valid"]
    
    # Tier 2: Fire Attribution (Tier 1 + Valid/Confirmed Satellite Scan)
    df["eligible_fire_attribution"] = df["eligible_baseline_environmental"] & df["firms_valid"]
    
    # Tier 3: BLH Ventilation (Tier 1 + 24h Complete BLH)
    df["eligible_blh_ventilation"] = df["eligible_baseline_environmental"] & df["era5_blh_valid"]
    
    # Tier 4: Full Multisource (Tier 1 + Valid Satellite + 24h Complete BLH)
    df["eligible_full_multisource"] = df["eligible_fire_attribution"] & df["era5_blh_valid"]

    # 7. Save outputs
    out_pq = PROCESSED_FINAL / "final_daily_data_quality_table.parquet"
    out_csv = PROCESSED_FINAL / "final_daily_data_quality_table.csv"
    audit_csv = AUDIT_FINAL / "FINAL_DAILY_DATA_QUALITY_TABLE.csv"
    
    df.to_parquet(out_pq, index=False)
    df.to_csv(out_csv, index=False)
    df.to_csv(audit_csv, index=False)
    
    print(f"\nSaved definitive data quality table to:")
    print(f"  - {out_pq}")
    print(f"  - {out_csv}")
    print(f"  - {audit_csv}")

    # Summary Statistics
    print("\n=== SUMMARY STATISTICS ===", flush=True)
    print(f"Total calendar days (2018-01-01 to 2025-12-31): {len(df):,}")
    print(f"CPCB Valid target days: {df['cpcb_valid'].sum():,}")
    print(f"ERA5 Core Weather valid days: {df['era5_basic_valid'].sum():,}")
    print(f"ERA5 24h Complete BLH valid days: {df['era5_blh_valid'].sum():,}")
    print(f"ERA5 Incomplete/Missing BLH days: {(~df['era5_blh_valid']).sum():,}")
    print("\nSatellite Observation Quality Breakdown:")
    print(df["satellite_observation_quality"].value_counts())
    print("\nModel Eligibility Tiers:")
    print(f"  Tier 1 (Baseline Environmental): {df['eligible_baseline_environmental'].sum():,} days")
    print(f"  Tier 2 (Fire Attribution):       {df['eligible_fire_attribution'].sum():,} days")
    print(f"  Tier 3 (BLH Ventilation):        {df['eligible_blh_ventilation'].sum():,} days")
    print(f"  Tier 4 (Full Multisource):       {df['eligible_full_multisource'].sum():,} days")

    # Save summary json
    summary = {
        "study_period": "2018-01-01 to 2025-12-31",
        "total_calendar_days": len(df),
        "cpcb_valid_days": int(df["cpcb_valid"].sum()),
        "severe_episodes_ge_250": int(df["is_severe_episode_ge_250"].sum()),
        "era5_core_weather_valid_days": int(df["era5_basic_valid"].sum()),
        "era5_blh_24h_complete_days": int(df["era5_blh_valid"].sum()),
        "era5_blh_incomplete_or_missing_days": int((~df["era5_blh_valid"]).sum()),
        "firms_b1_total_detections": len(df_b1),
        "firms_b2_cropland_detections": len(df_b2),
        "satellite_quality_counts": df["satellite_observation_quality"].value_counts().to_dict(),
        "model_eligibility_tiers": {
            "tier_1_baseline_environmental": int(df["eligible_baseline_environmental"].sum()),
            "tier_2_fire_attribution": int(df["eligible_fire_attribution"].sum()),
            "tier_3_blh_ventilation": int(df["eligible_blh_ventilation"].sum()),
            "tier_4_full_multisource": int(df["eligible_full_multisource"].sum())
        }
    }
    with open(AUDIT_FINAL / "FINAL_DATA_QUALITY_SUMMARY.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved summary JSON to {AUDIT_FINAL / 'FINAL_DATA_QUALITY_SUMMARY.json'}")

if __name__ == "__main__":
    build_data_quality_table()
