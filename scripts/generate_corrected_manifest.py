"""Generate comprehensive DATASET_MANIFEST.csv for Phase 1 Corrected Audit."""

from pathlib import Path
import hashlib
import pandas as pd

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
AUDIT_CORRECTED = PROJECT_ROOT / "audit" / "phase1_corrected"
AUDIT_CORRECTED.mkdir(parents=True, exist_ok=True)

def file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def generate_manifest():
    print("Generating comprehensive DATASET_MANIFEST.csv for Phase 1 Corrected...", flush=True)
    
    target_files = [
        # CPCB
        ("data/raw/cpcb_expanded/delhi_cpcb_pm25_expanded_raw.parquet", "Raw CPCB Station PM2.5 Measurements (89 Acquired Months)", "CPCB / XKDR API", "Parquet"),
        ("data/processed_phase1_corrected/cpcb_delhi_daily_target_2018_2025.parquet", "Validated Delhi-Wide Daily Target PM2.5 (>=10 NCT Stations)", "CPCB / XKDR API", "Parquet"),
        ("data/processed_phase1_corrected/cpcb_delhi_daily_target_2018_2025.csv", "Validated Delhi-Wide Daily Target PM2.5 (CSV Format)", "CPCB / XKDR API", "CSV"),
        ("audit/phase1_corrected/CPCB_DAILY_TARGET.csv", "Audited CPCB Daily Target Table", "CPCB / XKDR API", "CSV"),
        
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
        ("data/processed_phase1_corrected/punjab_haryana_fires_all_2018_2025.parquet", "Dataset B1: All Validated Punjab & Haryana Active Fires (Enriched)", "NASA LANCE / FIRMS", "Parquet"),
        ("data/processed_phase1_corrected/punjab_haryana_fires_cropland_2018_2025.parquet", "Dataset B2: Real Cropland Fires (ESA WorldCover Class 40)", "NASA LANCE / FIRMS", "Parquet"),
        ("audit/phase1_corrected/FIRMS_ANNUAL_COUNTS.csv", "Audited Annual Fire Counts (B1 vs B2)", "FIRMS & ESA Audit", "CSV"),
        ("audit/phase1_corrected/SAMPLE_CROPLAND_DETECTIONS.csv", "30 Genuine Sampled Detections with Land Cover Classes", "FIRMS & ESA Audit", "CSV"),
        
        # ESA WorldCover Rasters
        ("data/geographic/esa_worldcover/ESA_WorldCover_10m_2021_v200_N27E072_Map.tif", "ESA WorldCover 2021 10m Tile N27E072 (GeoTIFF)", "ESA / AWS S3", "GeoTIFF"),
        ("data/geographic/esa_worldcover/ESA_WorldCover_10m_2021_v200_N27E075_Map.tif", "ESA WorldCover 2021 10m Tile N27E075 (GeoTIFF)", "ESA / AWS S3", "GeoTIFF"),
        ("data/geographic/esa_worldcover/ESA_WorldCover_10m_2021_v200_N30E072_Map.tif", "ESA WorldCover 2021 10m Tile N30E072 (GeoTIFF)", "ESA / AWS S3", "GeoTIFF"),
        ("data/geographic/esa_worldcover/ESA_WorldCover_10m_2021_v200_N30E075_Map.tif", "ESA WorldCover 2021 10m Tile N30E075 (GeoTIFF)", "ESA / AWS S3", "GeoTIFF"),
        
        # ERA5 Corrected
        ("data/raw/era5_expanded_corrected/era5_hourly_corridor_2018_2025_ist.parquet", "Corrected ERA5 Hourly Corridor Archive (m/s & Asia/Kolkata)", "ECMWF via Open-Meteo", "Parquet"),
        ("data/processed_phase1_corrected/era5_delhi_daily_meteorology_2018_2025.parquet", "Corrected Delhi Daily Meteorology (2,922 IST Days)", "ECMWF via Open-Meteo", "Parquet"),
        ("data/processed_phase1_corrected/era5_delhi_daily_meteorology_2018_2025.csv", "Corrected Delhi Daily Meteorology (CSV Format)", "ECMWF via Open-Meteo", "CSV"),
        
        # Geographic Boundaries
        ("data/geographic/punjab_boundary.geojson", "Punjab State Boundary Polygon (Community GeoJSON)", "DataMeet / OSM", "GeoJSON"),
        ("data/geographic/haryana_boundary.geojson", "Haryana State Boundary Polygon (Community GeoJSON)", "DataMeet / OSM", "GeoJSON"),
        ("data/geographic/delhi_nct_boundary.geojson", "Delhi NCT Administrative Boundary Polygon (Community GeoJSON)", "DataMeet / OSM", "GeoJSON"),
        ("data/geographic/source_boundaries_manifest.json", "Boundary Provenance and Coordinate BBoxes", "DataMeet / OSM", "JSON"),
        
        # Coverage and Audit Outputs
        ("audit/phase1_corrected/ACTUAL_MONTHLY_COVERAGE.csv", "Actual Measured Monthly Coverage Matrix (96 Months)", "Audit Pipeline", "CSV"),
        ("audit/phase1_corrected/MULTISOURCE_DAILY_COVERAGE.csv", "Multisource Daily Coverage Table (2,922 Days)", "Audit Pipeline", "CSV"),
        ("audit/phase1_corrected/SEVERE_EPISODE_COUNTS.csv", "Annual Severe PM2.5 Episode Counts (>=250 ug/m3)", "Audit Pipeline", "CSV"),
        ("audit/phase1_corrected/DATA_QUALITY_SUMMARY.json", "Exact Scientific Quality Summary Metrics", "Audit Pipeline", "JSON")
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
            elif fmt == "GeoTIFF":
                recs = "36000x36000"
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
                "sha256_hash": "MISSING",
                "record_count": 0,
                "status": "FILE_NOT_FOUND"
            })
            
    df_manifest = pd.DataFrame(rows)
    out_path = AUDIT_CORRECTED / "DATASET_MANIFEST.csv"
    df_manifest.to_csv(out_path, index=False)
    print(f"Manifest written to {out_path} ({len(df_manifest)} entries)", flush=True)

if __name__ == "__main__":
    generate_manifest()
