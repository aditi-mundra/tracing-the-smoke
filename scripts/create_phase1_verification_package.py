"""
Creates audit/phase1/DATA_VERIFICATION_PACKAGE.zip
Packages all Phase 1 scripts, reports, manifests, geographic data, and sample authentic data tables.
"""
import os
import zipfile
import pandas as pd
from pathlib import Path

def create_verification_package():
    base_dir = Path("E:/AUCML_PROJECT")
    pkg_path = base_dir / "audit" / "phase1" / "DATA_VERIFICATION_PACKAGE.zip"
    samples_dir = base_dir / "audit" / "phase1" / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    
    print("Preparing authentic source data samples...")
    # 1. CPCB daily target
    cpcb_daily_src = base_dir / "data" / "processed_phase1" / "cpcb_delhi_daily_target_2018_2025.csv"
    if cpcb_daily_src.exists():
        df_cpcb = pd.read_csv(cpcb_daily_src)
        df_cpcb.head(500).to_csv(samples_dir / "sample_cpcb_delhi_daily_target.csv", index=False)
        print("  Sample CPCB daily target created.")
        
    # 2. CPCB station-day validated
    cpcb_stn_src = base_dir / "data" / "processed_phase1" / "cpcb_delhi_station_daily_validated_2018_2025.parquet"
    if cpcb_stn_src.exists():
        df_stn = pd.read_parquet(cpcb_stn_src)
        df_stn.head(1000).to_csv(samples_dir / "sample_cpcb_station_daily_validated.csv", index=False)
        print("  Sample CPCB station-day created.")
        
    # 3. ERA5 daily meteorology
    era5_src = base_dir / "data" / "processed_phase1" / "era5_delhi_daily_meteorology_2018_2025.parquet"
    if era5_src.exists():
        df_era5 = pd.read_parquet(era5_src)
        df_era5.head(500).to_csv(samples_dir / "sample_era5_delhi_daily.csv", index=False)
        print("  Sample ERA5 daily created.")
        
    # 4. FIRMS active fires sample
    firms_all_src = base_dir / "data" / "processed_phase1" / "punjab_haryana_fires_all_2018_2025.parquet"
    if firms_all_src.exists():
        df_f_all = pd.read_parquet(firms_all_src)
        df_f_all.head(1000).to_csv(samples_dir / "sample_firms_punjab_haryana_fires_all.csv", index=False)
        print("  Sample FIRMS all fires created.")
        
    firms_crop_src = base_dir / "data" / "processed_phase1" / "punjab_haryana_fires_cropland_2018_2025.parquet"
    if firms_crop_src.exists():
        df_f_crop = pd.read_parquet(firms_crop_src)
        df_f_crop.head(1000).to_csv(samples_dir / "sample_firms_punjab_haryana_fires_cropland.csv", index=False)
        print("  Sample FIRMS cropland fires created.")

    print(f"Creating ZIP archive at {pkg_path}...")
    files_to_include = []
    
    # Scripts
    scripts = [
        "scripts/acquire_boundaries.py",
        "scripts/download_cpcb_expanded.py",
        "scripts/download_firms_expanded.py",
        "scripts/download_era5_expanded.py",
        "scripts/patch_karnal_era5.py",
        "scripts/generate_cpcb_station_coverage_csv.py",
        "scripts/generate_dataset_manifest_phase1.py"
    ]
    for s in scripts:
        if (base_dir / s).exists():
            files_to_include.append((base_dir / s, f"scripts/{Path(s).name}"))
            
    # Geographic data
    geo_files = list((base_dir / "data" / "geographic").glob("*.*"))
    for g in geo_files:
        files_to_include.append((g, f"data/geographic/{g.name}"))
        
    # Audit reports
    audit_files = list((base_dir / "audit" / "phase1").glob("*.md")) + list((base_dir / "audit" / "phase1").glob("*.csv")) + list((base_dir / "audit" / "phase1").glob("*.log"))
    for a in audit_files:
        if a.name != "DATA_VERIFICATION_PACKAGE.zip":
            files_to_include.append((a, f"reports/{a.name}"))
            
    # Sample data
    sample_files = list(samples_dir.glob("*.csv"))
    for sm in sample_files:
        files_to_include.append((sm, f"samples/{sm.name}"))
        
    # Also include the complete CPCB daily target CSV if available
    if cpcb_daily_src.exists():
        files_to_include.append((cpcb_daily_src, "processed_data/cpcb_delhi_daily_target_2018_2025.csv"))

    with zipfile.ZipFile(pkg_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for src, arcname in files_to_include:
            zipf.write(src, arcname=arcname)
            print(f"  Added: {arcname} ({src.stat().st_size:,} bytes)")
            
    pkg_size_mb = pkg_path.stat().st_size / (1024 * 1024)
    print(f"\nSuccessfully generated {pkg_path} ({pkg_size_mb:.2f} MB)")
    print(f"Total files packaged: {len(files_to_include)}")

if __name__ == "__main__":
    create_verification_package()
