"""Package all Phase 1 Final Fixes deliverables into audit/phase1_final_fixes/CRITICAL_FIXES_PACKAGE.zip."""

from pathlib import Path
import zipfile
import pandas as pd

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
FINAL_FIXES_DIR = PROJECT_ROOT / "audit" / "phase1_final_fixes"
SAMPLES_DIR = FINAL_FIXES_DIR / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

PKG_PATH = FINAL_FIXES_DIR / "CRITICAL_FIXES_PACKAGE.zip"

def create_package():
    print("=== PACKAGING CRITICAL FIXES DELIVERABLES ===", flush=True)
    
    # 1. Create small authentic samples
    print("Preparing authentic source data samples...", flush=True)
    
    # Sample B1 with IST timestamps
    b1_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "punjab_haryana_fires_all_2018_2025.parquet"
    if b1_path.exists():
        df_b1 = pd.read_parquet(b1_path)
        sample_b1 = pd.concat([
            df_b1.head(500),
            df_b1[df_b1['acq_date'] != df_b1['date_ist']].head(500)
        ])
        sample_b1.to_csv(SAMPLES_DIR / "sample_firms_b1_all_fires_ist.csv", index=False)
        print("  Sample B1 (including midnight-crossing detections) created.", flush=True)
        
    # Sample B2 with IST timestamps
    b2_path = PROJECT_ROOT / "data" / "processed_phase1_corrected" / "punjab_haryana_fires_cropland_2018_2025.parquet"
    if b2_path.exists():
        df_b2 = pd.read_parquet(b2_path)
        sample_b2 = pd.concat([
            df_b2.head(500),
            df_b2[df_b2['acq_date'] != df_b2['date_ist']].head(500)
        ])
        sample_b2.to_csv(SAMPLES_DIR / "sample_firms_b2_cropland_fires_ist.csv", index=False)
        print("  Sample B2 (cropland fires with IST) created.", flush=True)

    # 2. Collect all files to package
    files_to_pack = []
    
    # Verification files and reports in audit/phase1_final_fixes/
    for f in FINAL_FIXES_DIR.glob("*.*"):
        if f.name != "CRITICAL_FIXES_PACKAGE.zip":
            files_to_pack.append((f, f"audit/{f.name}"))
            
    # Sample files
    for f in SAMPLES_DIR.glob("*.csv"):
        files_to_pack.append((f, f"samples/{f.name}"))
        
    # Corrected scripts
    scripts = [
        "verify_era5_blh_gap.py",
        "apply_firms_ist_timezone.py",
        "build_final_multisource_coverage.py",
        "generate_corrected_manifest.py",
        "correct_era5_hourly_daily.py",
        "build_monthly_and_daily_coverage_corrected.py",
        "apply_esa_cropland_filter.py",
    ]
    for s in scripts:
        sp = PROJECT_ROOT / "scripts" / s
        if sp.exists():
            files_to_pack.append((sp, f"scripts/{s}"))
            
    # Test suite
    tests = [
        "test_phase1_final_fixes.py",
        "test_phase1_corrected.py",
    ]
    for t in tests:
        tp = PROJECT_ROOT / "tests" / t
        if tp.exists():
            files_to_pack.append((tp, f"tests/{t}"))
            
    # Daily processed datasets (reasonably sized tables)
    daily_tables = [
        "delhi_weather_daily_2018_2025_ist.parquet",
        "delhi_weather_daily_2018_2025_ist.csv",
        "cpcb_delhi_daily_pm25_spatial_mean_2018_2025.parquet",
        "cpcb_delhi_daily_pm25_spatial_mean_2018_2025.csv",
        "final_daily_coverage_table.parquet",
        "final_daily_coverage_table.csv",
        "final_monthly_coverage_table.csv",
    ]
    for dt in daily_tables:
        dp = PROJECT_ROOT / "data" / "processed_phase1_corrected" / dt
        if dp.exists():
            files_to_pack.append((dp, f"daily_datasets/{dt}"))

    # Manifest
    manifest = PROJECT_ROOT / "audit" / "phase1_corrected" / "DATASET_MANIFEST.csv"
    if manifest.exists():
        files_to_pack.append((manifest, "audit/DATASET_MANIFEST.csv"))

    # 3. Write ZIP
    print(f"Creating ZIP archive at {PKG_PATH}...", flush=True)
    with zipfile.ZipFile(PKG_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
        for src, arc in files_to_pack:
            print(f"  Adding: {arc} ({src.stat().st_size:,} bytes)")
            zipf.write(src, arcname=arc)
            
    print(f"\nZIP Package successfully created: {PKG_PATH}")
    print(f"Total package size: {PKG_PATH.stat().st_size:,} bytes ({PKG_PATH.stat().st_size / (1024*1024):.2f} MB)")
    
    # Verify contents
    with zipfile.ZipFile(PKG_PATH, "r") as zipf:
        print(f"Total files in archive: {len(zipf.namelist())}")
        for item in zipf.infolist():
            print(f"  - {item.filename:50s} ({item.file_size:,} bytes -> {item.compress_size:,} bytes)")

if __name__ == "__main__":
    create_package()
