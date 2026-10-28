"""Generate CPCB_STATION_COVERAGE.csv for Phase 1 audit."""

from pathlib import Path
import json
import pandas as pd

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed_phase1"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
AUDIT_PHASE1 = PROJECT_ROOT / "audit" / "phase1"

def generate_station_coverage():
    print("Generating CPCB_STATION_COVERAGE.csv...")
    df_st = pd.read_parquet(PROCESSED_DIR / "cpcb_delhi_station_daily_validated_2018_2025.parquet")
    df_st["year"] = pd.to_datetime(df_st["period_start"]).dt.year
    
    with open(METADATA_DIR / "cpcb_delhi_nct_verified_stations.json", "r", encoding="utf-8") as f:
        station_meta = json.load(f)
        
    records = []
    for sid, meta in station_meta.items():
        sub = df_st[df_st["station_id"] == sid]
        yr_counts = sub["year"].value_counts().to_dict()
        
        records.append({
            "station_id": sid,
            "station_name": meta.get("station_name", "Unknown"),
            "latitude": meta.get("latitude"),
            "longitude": meta.get("longitude"),
            "in_delhi_nct": meta.get("in_delhi_nct", True),
            "total_valid_days_2018_2025": len(sub),
            "days_2018": yr_counts.get(2018, 0),
            "days_2019": yr_counts.get(2019, 0),
            "days_2020": yr_counts.get(2020, 0),
            "days_2021": yr_counts.get(2021, 0),
            "days_2022": yr_counts.get(2022, 0),
            "days_2023": yr_counts.get(2023, 0),
            "days_2024": yr_counts.get(2024, 0),
            "days_2025": yr_counts.get(2025, 0),
            "mean_pm25_ugm3": round(float(sub["mean"].mean()), 2) if len(sub) > 0 else 0.0,
            "min_pm25_ugm3": round(float(sub["mean"].min()), 2) if len(sub) > 0 else 0.0,
            "max_pm25_ugm3": round(float(sub["mean"].max()), 2) if len(sub) > 0 else 0.0
        })
        
    df_cov = pd.DataFrame(records).sort_values("total_valid_days_2018_2025", ascending=False)
    out_path = AUDIT_PHASE1 / "CPCB_STATION_COVERAGE.csv"
    df_cov.to_csv(out_path, index=False)
    print(f"Saved {len(df_cov)} station coverage records to {out_path}")

if __name__ == "__main__":
    generate_station_coverage()
