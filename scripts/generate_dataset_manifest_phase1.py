"""Generate comprehensive DATASET_MANIFEST.csv for Phase 1 audit."""

from pathlib import Path
import hashlib
import pandas as pd

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
PHASE1_AUDIT_DIR = PROJECT_ROOT / "audit" / "phase1"

def file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def generate_manifest():
    print("Generating comprehensive DATASET_MANIFEST.csv for Phase 1...")
    
    target_files = [
        # CPCB
        ("data/raw/cpcb_expanded/delhi_cpcb_pm25_expanded_raw.parquet", "Raw CPCB Station PM2.5 Measurements (92 Months)", "CPCB / XKDR API", "Parquet"),
        ("data/processed_phase1/cpcb_delhi_station_daily_validated_2018_2025.parquet", "Validated Delhi NCT Station Daily PM2.5 (>=16h QC)", "CPCB / XKDR API", "Parquet"),
        ("data/processed_phase1/cpcb_delhi_daily_target_2018_2025.parquet", "Delhi-Wide Daily Target PM2.5 (>=10 NCT Stations)", "CPCB / XKDR API", "Parquet"),
        ("data/processed_phase1/cpcb_delhi_daily_target_2018_2025.csv", "Delhi-Wide Daily Target PM2.5 (CSV Format)", "CPCB / XKDR API", "CSV"),
        
        # ERA5
        ("data/raw/era5_expanded/era5_hourly_corridor_2018_2025.parquet", "ERA5 Hourly Reanalysis Corridor (4 Locations, 280,512 Hours)", "ECMWF via Open-Meteo", "Parquet"),
        ("data/processed_phase1/era5_delhi_daily_meteorology_2018_2025.parquet", "Delhi Daily Meteorology & Derived Vector Features", "ECMWF via Open-Meteo", "Parquet"),
        ("data/processed_phase1/era5_delhi_daily_meteorology_2018_2025.csv", "Delhi Daily Meteorology & Derived Vector Features (CSV)", "ECMWF via Open-Meteo", "CSV"),
        
        # Geographic Boundaries
        ("data/geographic/punjab_boundary.geojson", "Punjab State Boundary Polygon", "Survey of India / DataMeet", "GeoJSON"),
        ("data/geographic/haryana_boundary.geojson", "Haryana State Boundary Polygon", "Survey of India / DataMeet", "GeoJSON"),
        ("data/geographic/delhi_nct_boundary.geojson", "Delhi NCT Administrative Boundary Polygon", "Survey of India / DataMeet", "GeoJSON"),
        ("data/geographic/source_boundaries_manifest.json", "Boundary Provenance and Coordinate BBoxes", "Audit Pipeline", "JSON"),
        
        # FIRMS Raw Archives
        ("data/raw/firms_annual/viirs-snpp_2018_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2018", "NASA LANCE / EOSDIS", "CSV"),
        ("data/raw/firms_annual/viirs-snpp_2019_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2019", "NASA LANCE / EOSDIS", "CSV"),
        ("data/raw/firms_annual/viirs-snpp_2020_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2020", "NASA LANCE / EOSDIS", "CSV"),
        ("data/raw/firms_annual/viirs-snpp_2021_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2021", "NASA LANCE / EOSDIS", "CSV"),
        ("data/raw/firms_annual/viirs-snpp_2022_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2022", "NASA LANCE / EOSDIS", "CSV"),
        ("data/raw/firms_annual/viirs-snpp_2023_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2023", "NASA LANCE / EOSDIS", "CSV"),
        ("data/raw/firms_annual/viirs-snpp_2024_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2024", "NASA LANCE / EOSDIS", "CSV"),
        ("data/raw/firms_annual/viirs-snpp_2025_India.csv", "NASA FIRMS VIIRS 375m Annual India Archive 2025", "NASA LANCE / EOSDIS", "CSV"),
        
        # FIRMS Processed
        ("data/processed_phase1/punjab_haryana_fires_all_2018_2025.parquet", "Dataset B1: All Validated Punjab & Haryana Active Fires", "NASA LANCE / FIRMS", "Parquet"),
        ("data/processed_phase1/punjab_haryana_fires_cropland_2018_2025.parquet", "Dataset B2: Cropland Likely Agricultural Fires", "NASA LANCE / FIRMS", "Parquet"),
    ]
    
    rows = []
    for rel_path, desc, source, fmt in target_files:
        p = PROJECT_ROOT / rel_path
        if p.exists():
            size = p.stat().st_size
            sha = file_sha256(p)
            
            # Determine record count
            if fmt == "Parquet":
                df = pd.read_parquet(p)
                recs = len(df)
            elif fmt == "CSV":
                recs = sum(1 for _ in open(p, "rb")) - 1
            elif fmt in ("GeoJSON", "JSON"):
                recs = 1
            else:
                recs = "N/A"
                
            rows.append({
                "file_path": rel_path,
                "description": desc,
                "source_provider": source,
                "file_format": fmt,
                "file_size_bytes": size,
                "file_size_mb": round(size / (1024 * 1024), 2),
                "sha256_hash": sha,
                "record_count": recs,
                "status": "ACQUIRED_AND_VERIFIED"
            })
        else:
            rows.append({
                "file_path": rel_path,
                "description": desc,
                "source_provider": source,
                "file_format": fmt,
                "file_size_bytes": 0,
                "file_size_mb": 0.0,
                "sha256_hash": "PENDING_EXECUTION",
                "record_count": 0,
                "status": "DOWNLOADING_OR_PROCESSING"
            })
            
    df_manifest = pd.DataFrame(rows)
    out_path = PHASE1_AUDIT_DIR / "DATASET_MANIFEST.csv"
    df_manifest.to_csv(out_path, index=False)
    print(f"Manifest written to {out_path} ({len(df_manifest)} entries)")

if __name__ == "__main__":
    generate_manifest()
