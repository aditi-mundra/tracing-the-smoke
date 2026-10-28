"""Package all Phase 1 Corrected deliverables into audit/phase1_corrected/FINAL_VERIFICATION_PACKAGE.zip."""

from pathlib import Path
import zipfile
import pandas as pd

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
AUDIT_CORRECTED = PROJECT_ROOT / "audit" / "phase1_corrected"
SAMPLES_DIR = AUDIT_CORRECTED / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

PKG_PATH = AUDIT_CORRECTED / "FINAL_VERIFICATION_PACKAGE.zip"

def create_package():
    print("=== PACKAGING FINAL VERIFICATION DELIVERABLES ===", flush=True)
    
    # 1. Create small authentic samples
    print("Preparing authentic source data samples...", flush=True)
    
    # Sample B1
    b1_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "punjab_haryana_fires_all_2018_2025.parquet"
    if b1_path.exists():
        df_b1 = pd.read_parquet(b1_path)
        df_b1.head(1000).to_csv(SAMPLES_DIR / "sample_firms_b1_all_fires.csv", index=False)
        print("  Sample B1 created.", flush=True)
        
    # Sample B2
    b2_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "punjab_haryana_fires_cropland_2018_2025.parquet"
    if b2_path.exists():
        df_b2 = pd.read_parquet(b2_path)
        df_b2.head(1000).to_csv(SAMPLES_DIR / "sample_firms_b2_cropland_fires.csv", index=False)
        print("  Sample B2 created.", flush=True)
        
    # Sample CPCB station-day
    stn_path = PROJECT_ROOT / "data" / "processed_phase1" / "cpcb_delhi_station_daily_validated_2018_2025.parquet"
    if stn_path.exists():
        df_stn = pd.read_parquet(stn_path)
        df_stn.head(1000).to_csv(SAMPLES_DIR / "sample_cpcb_station_daily.csv", index=False)
        print("  Sample CPCB station-day created.", flush=True)
        
    # Sample ERA5 corridor hourly
    era5_corridor_path = PROJECT_ROOT / "data" / "raw" / "era5_expanded_corrected" / "era5_hourly_corridor_2018_2025_ist.parquet"
    if era5_corridor_path.exists():
        df_era5_h = pd.read_parquet(era5_corridor_path)
        df_era5_h.head(1000).to_csv(SAMPLES_DIR / "sample_era5_corridor_hourly_ist.csv", index=False)
        print("  Sample ERA5 corridor hourly created.", flush=True)

    # 2. Collect all files to package
    files_to_pack = []
    
    # Reports and audit deliverables
    for f in AUDIT_CORRECTED.glob("*.*"):
        if f.name != "FINAL_VERIFICATION_PACKAGE.zip":
            files_to_pack.append((f, f"reports/{f.name}"))
            
    # Sample files
    for f in SAMPLES_DIR.glob("*.csv"):
        files_to_pack.append((f, f"samples/{f.name}"))
        
    # Scripts
    scripts = [
        "scripts/download_esa_worldcover_tiles.py",
        "scripts/apply_esa_cropland_filter.py",
        "scripts/correct_era5_hourly_daily.py",
        "scripts/validate_and_generate_cpcb_outputs.py",
        "scripts/build_monthly_and_daily_coverage_corrected.py",
        "scripts/generate_corrected_manifest.py",
        "scripts/download_cpcb_expanded.py",
        "scripts/download_firms_expanded.py",
        "scripts/acquire_boundaries.py"
    ]
    for s in scripts:
        sp = PROJECT_ROOT / s
        if sp.exists():
            files_to_pack.append((sp, f"scripts/{sp.name}"))
            
    # Test suite
    test_file = PROJECT_ROOT / "tests" / "test_phase1_corrected.py"
    if test_file.exists():
        files_to_pack.append((test_file, "tests/test_phase1_corrected.py"))
        
    # Geographic boundaries
    for g in (PROJECT_ROOT / "data" / "geographic").glob("*.geojson"):
        files_to_pack.append((g, f"data/geographic/{g.name}"))
    g_manifest = PROJECT_ROOT / "data" / "geographic" / "source_boundaries_manifest.json"
    if g_manifest.exists():
        files_to_pack.append((g_manifest, "data/geographic/source_boundaries_manifest.json"))
        
    # Corrected full datasets (CSV format)
    cpcb_target_csv = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "cpcb_delhi_daily_target_2018_2025.csv"
    if cpcb_target_csv.exists():
        files_to_pack.append((cpcb_target_csv, "processed_data/cpcb_delhi_daily_target_2018_2025.csv"))
        
    era5_target_csv = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "era5_delhi_daily_meteorology_2018_2025.csv"
    if era5_target_csv.exists():
        files_to_pack.append((era5_target_csv, "processed_data/era5_delhi_daily_meteorology_2018_2025.csv"))
        
    # 3. Write ZIP archive
    print(f"\nWriting ZIP archive to {PKG_PATH}...", flush=True)
    with zipfile.ZipFile(PKG_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
        for src, arcname in files_to_pack:
            zipf.write(src, arcname=arcname)
            print(f"  + {arcname} ({src.stat().st_size:,} bytes)", flush=True)
            
    size_mb = PKG_PATH.stat().st_size / (1024 * 1024)
    print(f"\nSuccessfully generated {PKG_PATH} ({size_mb:.2f} MB)", flush=True)
    print(f"Total packaged files: {len(files_to_pack)}", flush=True)

if __name__ == "__main__":
    create_package()
