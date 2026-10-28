"""Build Final Multisource Daily Coverage Table with Granular Eligibility Tiers.
Resolves FIX 3:
- Rebuilds coverage across all 2,922 calendar days (2018-01-01 to 2025-12-31).
- Distinguishes confirmed zero fires from satellite product data gaps.
- Distinguishes complete basic meteorology from the 181-day BLH archive gap in 2024.
- Generates 4 explicit modeling eligibility flags:
    1. eligible_baseline_environmental (CPCB target + basic weather)
    2. eligible_fire_attribution (CPCB target + basic weather + satellite fire scan)
    3. eligible_blh_ventilation (CPCB target + basic weather + BLH/ventilation index)
    4. eligible_full_multisource (All 3 streams complete)
- Produces:
    audit/phase1_final_fixes/FINAL_MULTISOURCE_COVERAGE.csv
    audit/phase1_final_fixes/FINAL_DATA_QUALITY_SUMMARY.json
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PROCESSED_CORRECTED = PROJECT_ROOT / "data" / "processed_phase1_corrected"
RAW_FIRMS_DIR = PROJECT_ROOT / "data" / "raw" / "firms_annual"
AUDIT_FINAL_DIR = PROJECT_ROOT / "audit" / "phase1_final_fixes"
AUDIT_FINAL_DIR.mkdir(parents=True, exist_ok=True)

def build_final_coverage():
    print("=== BUILDING FINAL MULTISOURCE DAILY COVERAGE TABLE ===", flush=True)
    
    # 1. CPCB Target (2,709 valid days)
    df_cpcb = pd.read_parquet(PROCESSED_CORRECTED / "cpcb_delhi_daily_target_2018_2025.parquet")
    cpcb_map = df_cpcb.set_index("date_str").to_dict(orient="index")
    print(f"Loaded {len(df_cpcb):,} CPCB daily target records", flush=True)
    
    # 2. ERA5 Delhi Daily Meteorology (2,922 days, with 181 BLH gap in H1 2024)
    df_era5 = pd.read_parquet(PROCESSED_CORRECTED / "era5_delhi_daily_meteorology_2018_2025.parquet")
    era5_map = df_era5.set_index("date_ist").to_dict(orient="index")
    print(f"Loaded {len(df_era5):,} ERA5 daily weather records", flush=True)
    
    # 3. FIRMS Detections in IST
    df_b1 = pd.read_parquet(PROCESSED_CORRECTED / "punjab_haryana_fires_all_2018_2025.parquet")
    df_b2 = pd.read_parquet(PROCESSED_CORRECTED / "punjab_haryana_fires_cropland_2018_2025.parquet")
    
    b1_ist_counts = df_b1.groupby("date_ist").size().to_dict()
    b2_ist_counts = df_b2.groupby("date_ist").size().to_dict()
    b1_ist_frp_sum = df_b1.groupby("date_ist")["frp"].sum().to_dict()
    b2_ist_frp_sum = df_b2.groupby("date_ist")["frp"].sum().to_dict()
    
    # 4. India Country-Level Detections in IST to identify satellite data gaps vs 0 fires
    print("Parsing India-level fire activity in IST across all 8 annual archives...", flush=True)
    india_daily_counts = {}
    for yr in range(2018, 2026):
        raw_csv = RAW_FIRMS_DIR / f"viirs-snpp_{yr}_India.csv"
        df_ind = pd.read_csv(raw_csv, usecols=["acq_date", "acq_time"])
        hh = df_ind["acq_time"] // 100
        mm = df_ind["acq_time"] % 100
        time_str = df_ind["acq_date"] + " " + hh.astype(str).str.zfill(2) + ":" + mm.astype(str).str.zfill(2) + ":00"
        dt_ist = pd.to_datetime(time_str) + pd.Timedelta(hours=5, minutes=30)
        daily_c = dt_ist.dt.strftime("%Y-%m-%d").value_counts().to_dict()
        for d, c in daily_c.items():
            india_daily_counts[d] = india_daily_counts.get(d, 0) + c
            
    print(f"Computed India fire counts for {len(india_daily_counts):,} distinct IST dates", flush=True)
    
    # 5. Build Unified Daily Matrix (2,922 calendar days)
    all_dates = pd.date_range("2018-01-01", "2025-12-31", freq="D")
    rows = []
    
    for dt in all_dates:
        d_str = dt.strftime("%Y-%m-%d")
        yr = dt.year
        mo = dt.month
        dy = dt.day
        
        # Season classification
        if mo in [10, 11]:
            season = "Peak Paddy Harvest Burning (Oct-Nov)"
        elif mo in [9, 12]:
            season = "Post-Monsoon / Early Winter (Sep/Dec)"
        elif mo in [4, 5]:
            season = "Wheat Harvest Burning (Apr-May)"
        elif mo in [6, 7, 8]:
            season = "Monsoon Baseline (Jun-Aug)"
        else:
            season = "Winter / Pre-Monsoon Baseline (Jan-Mar)"
            
        # A. CPCB Status
        cpcb_rec = cpcb_map.get(d_str)
        cpcb_valid = cpcb_rec is not None and cpcb_rec.get("is_valid_city_target", False)
        pm25_target = round(cpcb_rec["delhi_pm25_target"], 2) if cpcb_valid else np.nan
        active_stns = cpcb_rec["active_station_count"] if cpcb_valid else 0
        is_severe = (pm25_target >= 250.0) if cpcb_valid else False
        
        # B. ERA5 Weather Status
        era5_rec = era5_map.get(d_str)
        era5_basic_valid = era5_rec is not None and not np.isnan(era5_rec.get("temp_mean", np.nan))
        temp_val = round(era5_rec["temp_mean"], 2) if era5_basic_valid else np.nan
        wspd_val = round(era5_rec["wind_speed_mean"], 2) if era5_basic_valid else np.nan
        wdir_val = round(era5_rec["prevailing_wind_direction_deg"], 1) if era5_basic_valid else np.nan
        
        blh_val = era5_rec.get("blh_mean", np.nan) if era5_rec else np.nan
        era5_blh_valid = era5_basic_valid and not np.isnan(blh_val)
        vent_val = round(era5_rec.get("ventilation_index", np.nan), 2) if era5_blh_valid else np.nan
        blh_val_round = round(blh_val, 2) if era5_blh_valid else np.nan
        
        # C. FIRMS Satellite Status
        india_fires = india_daily_counts.get(d_str, 0)
        firms_scan_valid = india_fires > 0
        
        b1_cnt = b1_ist_counts.get(d_str, 0)
        b2_cnt = b2_ist_counts.get(d_str, 0)
        b1_frp = round(b1_ist_frp_sum.get(d_str, 0.0), 2)
        b2_frp = round(b2_ist_frp_sum.get(d_str, 0.0), 2)
        
        if firms_scan_valid:
            if b1_cnt > 0:
                firms_obs_status = "FIRES_DETECTED"
            else:
                firms_obs_status = "CONFIRMED_ZERO_FIRES"
        else:
            firms_obs_status = "SATELLITE_DATA_GAP"
            
        # D. Eligibility Tiers
        tier1_eligible = cpcb_valid and era5_basic_valid
        tier2_eligible = cpcb_valid and era5_basic_valid and firms_scan_valid
        tier3_eligible = cpcb_valid and era5_basic_valid and era5_blh_valid
        tier4_eligible = cpcb_valid and era5_basic_valid and era5_blh_valid and firms_scan_valid
        
        rows.append({
            "date_ist": d_str,
            "year": yr,
            "month": mo,
            "day": dy,
            "season": season,
            "cpcb_valid": cpcb_valid,
            "delhi_pm25_target": pm25_target,
            "active_cpcb_stations": active_stns,
            "is_severe_episode_ge_250": is_severe,
            "era5_basic_valid": era5_basic_valid,
            "era5_temp_mean_c": temp_val,
            "era5_wind_speed_mean_ms": wspd_val,
            "era5_wind_direction_deg": wdir_val,
            "era5_blh_valid": era5_blh_valid,
            "era5_blh_mean_m": blh_val_round,
            "era5_ventilation_index_m2s": vent_val,
            "firms_satellite_scan_valid": firms_scan_valid,
            "firms_observation_status": firms_obs_status,
            "firms_india_detections": india_fires,
            "firms_b1_fires_ist": b1_cnt,
            "firms_b2_cropland_fires_ist": b2_cnt,
            "firms_b1_frp_sum_mw": b1_frp,
            "firms_b2_cropland_frp_sum_mw": b2_frp,
            "eligible_baseline_environmental": tier1_eligible,
            "eligible_fire_attribution": tier2_eligible,
            "eligible_blh_ventilation": tier3_eligible,
            "eligible_full_multisource": tier4_eligible
        })
        
    df_final = pd.DataFrame(rows)
    out_csv = AUDIT_FINAL_DIR / "FINAL_MULTISOURCE_COVERAGE.csv"
    df_final.to_csv(out_csv, index=False)
    print(f"\nSaved FINAL_MULTISOURCE_COVERAGE.csv to {out_csv} ({len(df_final)} rows)", flush=True)
    
    # 6. Generate FINAL_DATA_QUALITY_SUMMARY.json
    t1_cnt = int(df_final["eligible_baseline_environmental"].sum())
    t2_cnt = int(df_final["eligible_fire_attribution"].sum())
    t3_cnt = int(df_final["eligible_blh_ventilation"].sum())
    t4_cnt = int(df_final["eligible_full_multisource"].sum())
    
    summary = {
        "study_period": "2018-01-01 to 2025-12-31",
        "total_calendar_days": len(df_final),
        "source_streams_summary": {
            "cpcb_delhi_pm25_valid_days": int(df_final["cpcb_valid"].sum()),
            "cpcb_unarchived_missing_days": int((~df_final["cpcb_valid"]).sum()),
            "era5_basic_meteo_valid_days": int(df_final["era5_basic_valid"].sum()),
            "era5_blh_valid_days": int(df_final["era5_blh_valid"].sum()),
            "era5_blh_2024_gap_days": int((~df_final["era5_blh_valid"]).sum()),
            "firms_valid_satellite_scans_days": int(df_final["firms_satellite_scan_valid"].sum()),
            "firms_satellite_gap_days": int((~df_final["firms_satellite_scan_valid"]).sum()),
            "firms_confirmed_zero_fires_days": int((df_final["firms_observation_status"] == "CONFIRMED_ZERO_FIRES").sum()),
            "firms_fires_detected_days": int((df_final["firms_observation_status"] == "FIRES_DETECTED").sum())
        },
        "model_eligibility_tiers": {
            "tier1_baseline_environmental_model": {
                "description": "Requires valid Delhi PM2.5 target and basic ERA5 weather (T, RH, Pressure, Vector Winds).",
                "usable_days": t1_cnt,
                "pct_of_target_days": round((t1_cnt / 2709) * 100.0, 2)
            },
            "tier2_fire_attribution_model": {
                "description": "Requires valid Delhi PM2.5 target, basic ERA5 weather, and active FIRMS satellite coverage.",
                "usable_days": t2_cnt,
                "pct_of_target_days": round((t2_cnt / 2709) * 100.0, 2)
            },
            "tier3_blh_ventilation_model": {
                "description": "Requires valid Delhi PM2.5 target, basic ERA5 weather, and valid BLH/Ventilation index.",
                "usable_days": t3_cnt,
                "pct_of_target_days": round((t3_cnt / 2709) * 100.0, 2)
            },
            "tier4_full_multisource_model": {
                "description": "Requires valid Delhi PM2.5 target, complete ERA5 weather including BLH, and active FIRMS satellite scan.",
                "usable_days": t4_cnt,
                "pct_of_target_days": round((t4_cnt / 2709) * 100.0, 2)
            }
        },
        "seasonal_breakdown_tier4": {
            "post_monsoon_sep_dec_days": int(df_final[df_final["eligible_full_multisource"] & df_final["month"].isin([9, 10, 11, 12]) & (df_final["year"] <= 2024)].shape[0]),
            "peak_paddy_oct_nov_days": int(df_final[df_final["eligible_full_multisource"] & df_final["month"].isin([10, 11]) & (df_final["year"] <= 2024)].shape[0]),
            "wheat_harvest_apr_may_days": int(df_final[df_final["eligible_full_multisource"] & df_final["month"].isin([4, 5])].shape[0]),
            "severe_pollution_episodes_tier4": int(df_final[df_final["eligible_full_multisource"] & df_final["is_severe_episode_ge_250"]].shape[0])
        }
    }
    
    out_json = AUDIT_FINAL_DIR / "FINAL_DATA_QUALITY_SUMMARY.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved FINAL_DATA_QUALITY_SUMMARY.json to {out_json}", flush=True)
    
    print("\n--- SUMMARY OF FINAL MODEL ELIGIBILITY TIERS ---")
    print(f"  Tier 1 (Baseline Environmental): {t1_cnt} days")
    print(f"  Tier 2 (Fire Attribution):       {t2_cnt} days")
    print(f"  Tier 3 (BLH Ventilation):        {t3_cnt} days")
    print(f"  Tier 4 (Full Multisource):       {t4_cnt} days")

if __name__ == "__main__":
    build_final_coverage()
