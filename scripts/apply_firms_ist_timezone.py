"""NASA FIRMS Active Fires UTC-to-IST Timezone Alignment.
Resolves FIX 2:
- Combines acq_date and acq_time into full timestamp_utc.
- Converts to Indian Standard Time (timestamp_ist = timestamp_utc + 5h30m).
- Generates date_ist, year_ist, and month_ist.
- Updates processed B1 and B2 Parquet tables.
- Produces audit/phase1_final_fixes/FIRMS_IST_ALIGNMENT_CHECK.csv documenting boundary shifts.
"""

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed_phase1_corrected"
AUDIT_FINAL_DIR = PROJECT_ROOT / "audit" / "phase1_final_fixes"
AUDIT_CORRECTED_DIR = PROJECT_ROOT / "audit" / "phase1_corrected"

AUDIT_FINAL_DIR.mkdir(parents=True, exist_ok=True)

def apply_firms_ist_timezone():
    print("=== STARTING NASA FIRMS UTC-TO-IST TIMEZONE ALIGNMENT ===", flush=True)
    
    b1_path = PROCESSED_DIR / "punjab_haryana_fires_all_2018_2025.parquet"
    b2_path = PROCESSED_DIR / "punjab_haryana_fires_cropland_2018_2025.parquet"
    
    if not b1_path.exists():
        raise FileNotFoundError(f"Missing {b1_path}")
        
    print(f"Loading Dataset B1 from {b1_path}...", flush=True)
    df_b1 = pd.read_parquet(b1_path)
    
    # 1. Parse UTC timestamp
    hh = df_b1["acq_time"] // 100
    mm = df_b1["acq_time"] % 100
    time_str = df_b1["acq_date"] + " " + hh.astype(str).str.zfill(2) + ":" + mm.astype(str).str.zfill(2) + ":00"
    df_b1["timestamp_utc"] = pd.to_datetime(time_str)
    
    # 2. Add 5 hours 30 minutes for Asia/Kolkata
    df_b1["timestamp_ist"] = df_b1["timestamp_utc"] + pd.Timedelta(hours=5, minutes=30)
    df_b1["date_ist"] = df_b1["timestamp_ist"].dt.strftime("%Y-%m-%d")
    df_b1["year_ist"] = df_b1["timestamp_ist"].dt.year
    df_b1["month_ist"] = df_b1["timestamp_ist"].dt.month
    
    # Analyze shift
    shifted_mask = df_b1["acq_date"] != df_b1["date_ist"]
    shifted_count = int(shifted_mask.sum())
    total_count = len(df_b1)
    shift_pct = (shifted_count / total_count) * 100.0
    print(f"Total fire detections: {total_count:,}")
    print(f"Detections shifting across UTC midnight to next IST date: {shifted_count:,} ({shift_pct:.2f}%)", flush=True)
    
    # Save updated B1
    df_b1.to_parquet(b1_path, index=False, compression="snappy")
    print(f"Saved updated Dataset B1 to {b1_path}", flush=True)
    
    # 3. Update Dataset B2
    print("Updating Dataset B2 (cropland subset)...", flush=True)
    df_b2 = df_b1[df_b1["is_cropland"] == True].copy()
    df_b2.to_parquet(b2_path, index=False, compression="snappy")
    print(f"Saved updated Dataset B2 to {b2_path} ({len(df_b2):,} records)", flush=True)
    
    # 4. Generate FIRMS_IST_ALIGNMENT_CHECK.csv
    print("Generating timezone alignment audit table...", flush=True)
    # 50 shifted samples (nighttime pass between 18:30 and 23:59 UTC)
    sample_shifted = df_b1[shifted_mask].sample(50, random_state=42).copy()
    sample_shifted["shifted_to_next_day_ist"] = True
    
    # 20 daytime samples (afternoon pass around 07:00-09:00 UTC = 12:30-14:30 IST)
    sample_day = df_b1[~shifted_mask].sample(20, random_state=42).copy()
    sample_day["shifted_to_next_day_ist"] = False
    
    sample_audit = pd.concat([sample_shifted, sample_day], ignore_index=True)
    cols_audit = [
        "acq_date", "acq_time", "timestamp_utc", "timestamp_ist", "date_ist",
        "state", "latitude", "longitude", "frp", "confidence", "land_cover_name",
        "is_cropland", "shifted_to_next_day_ist"
    ]
    audit_csv = AUDIT_FINAL_DIR / "FIRMS_IST_ALIGNMENT_CHECK.csv"
    sample_audit[cols_audit].to_csv(audit_csv, index=False)
    print(f"Saved alignment verification samples to {audit_csv} ({len(sample_audit)} rows)", flush=True)
    
    # 5. Recompute Annual Counts using year_ist
    raw_india_totals = {
        2018: 650470, 2019: 537746, 2020: 489632, 2021: 771938,
        2022: 591594, 2023: 579733, 2024: 552312, 2025: 646376
    }
    annual_rows = []
    for yr in sorted(df_b1["year_ist"].unique()):
        df_yr = df_b1[df_b1["year_ist"] == yr]
        b1_cnt = len(df_yr)
        b2_cnt = len(df_yr[df_yr["is_cropland"] == True])
        non_crop = b1_cnt - b2_cnt
        unclass = len(df_yr[df_yr["land_cover_class"] == 0])
        punjab_cnt = len(df_yr[df_yr["state"] == "punjab"])
        haryana_cnt = len(df_yr[df_yr["state"] == "haryana"])
        ret_pct = round((b2_cnt / max(b1_cnt, 1)) * 100.0, 2)
        
        annual_rows.append({
            "year_ist": yr,
            "india_total_raw_detections": raw_india_totals.get(yr, 0),
            "punjab_polygon_detections": punjab_cnt,
            "haryana_polygon_detections": haryana_cnt,
            "dataset_b1_total_ist": b1_cnt,
            "dataset_b2_cropland_detected_ist": b2_cnt,
            "non_cropland_detections": non_crop,
            "unclassified_detections": unclass,
            "cropland_retention_pct": ret_pct,
            "satellite_product": "VIIRS S-NPP 375m (VNP14IMGTDL)",
            "timezone": "Asia/Kolkata (UTC+05:30)"
        })
    df_annual = pd.DataFrame(annual_rows)
    df_annual.to_csv(AUDIT_FINAL_DIR / "FIRMS_ANNUAL_COUNTS_IST.csv", index=False)
    print("\nUpdated Annual Fire Counts in Indian Standard Time (IST):")
    print(df_annual[["year_ist", "dataset_b1_total_ist", "dataset_b2_cropland_detected_ist", "cropland_retention_pct"]])
    
    return df_b1, sample_audit

if __name__ == "__main__":
    apply_firms_ist_timezone()
