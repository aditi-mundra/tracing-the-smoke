"""ESA WorldCover 2021 Real Cropland Filtering for NASA FIRMS VIIRS Active Fires (2018 - 2025).
Resolves Issue 1:
- Uses authentic ESA WorldCover 2021 10m Land Cover GeoTIFFs covering Punjab and Haryana.
- Samples the exact 10m pixel class (Class 40: Cropland) using Rasterio.
- Replaces previous arbitrary FRP and urban-radius heuristics with real land cover classification.
- Preserves dual datasets:
    Dataset B1: All validated active fires in Punjab and Haryana (enriched with land_cover_class)
    Dataset B2: Active fires intersecting confirmed cropland pixels (Class 40)
- Outputs detailed sampling audit table with >= 20 genuine samples and annual counts.
"""

from pathlib import Path
import json
import rasterio
import pandas as pd
import numpy as np

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
ESA_DIR = PROJECT_ROOT / "data" / "geographic" / "esa_worldcover"
PROCESSED_B1_SRC = PROJECT_ROOT / "data" / "processed_phase1" / "punjab_haryana_fires_all_2018_2025.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_phase1_corrected"
AUDIT_DIR = PROJECT_ROOT / "audit" / "phase1_corrected"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

ESA_CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
    0: "No data / Unclassified"
}

TILES = [
    {"name": "N27E072", "bounds": (72.0, 27.0, 75.0, 30.0), "filename": "ESA_WorldCover_10m_2021_v200_N27E072_Map.tif"},
    {"name": "N27E075", "bounds": (75.0, 27.0, 78.0, 30.0), "filename": "ESA_WorldCover_10m_2021_v200_N27E075_Map.tif"},
    {"name": "N30E072", "bounds": (72.0, 30.0, 75.0, 33.0), "filename": "ESA_WorldCover_10m_2021_v200_N30E072_Map.tif"},
    {"name": "N30E075", "bounds": (75.0, 30.0, 78.0, 33.0), "filename": "ESA_WorldCover_10m_2021_v200_N30E075_Map.tif"}
]

def apply_cropland_filter():
    print("=== STARTING REAL ESA WORLDCOVER 10m CROPLAND CLASSIFICATION ===", flush=True)
    
    if not PROCESSED_B1_SRC.exists():
        raise FileNotFoundError(f"Source B1 dataset not found at {PROCESSED_B1_SRC}")
        
    print(f"Loading Dataset B1: {PROCESSED_B1_SRC}...", flush=True)
    df_fires = pd.read_parquet(PROCESSED_B1_SRC)
    print(f"Total input fires: {len(df_fires):,} records (2018 - 2025)", flush=True)
    
    # Initialize classification columns
    df_fires["land_cover_class"] = 0
    df_fires["is_cropland"] = False
    
    # Process tile by tile to optimize memory and speed
    for tile_info in TILES:
        t_name = tile_info["name"]
        t_file = ESA_DIR / tile_info["filename"]
        min_lon, min_lat, max_lon, max_lat = tile_info["bounds"]
        
        if not t_file.exists():
            raise FileNotFoundError(f"ESA WorldCover tile missing: {t_file}")
            
        # Identify subset of fires falling within this tile's geographic envelope
        mask = (
            (df_fires["longitude"] >= min_lon) & (df_fires["longitude"] < max_lon) &
            (df_fires["latitude"] >= min_lat) & (df_fires["latitude"] < max_lat)
        )
        subset_idx = df_fires[mask].index
        count_in_tile = len(subset_idx)
        print(f"\n[{t_name}] Processing {count_in_tile:,} fires intersecting bounds [{min_lat}-{max_lat}N, {min_lon}-{max_lon}E]...", flush=True)
        
        if count_in_tile == 0:
            continue
            
        sub_lons = df_fires.loc[subset_idx, "longitude"].values
        sub_lats = df_fires.loc[subset_idx, "latitude"].values
        
        # Read tile with rasterio
        with rasterio.open(t_file) as src:
            transform = src.transform
            nodata = src.nodata
            # Invert transform: coords -> row, col
            inv_transform = ~transform
            
            # Compute pixel rows and cols
            xs, ys = sub_lons, sub_lats
            cols, rows = inv_transform * (xs, ys)
            cols = np.floor(cols).astype(int)
            rows = np.floor(rows).astype(int)
            
            # Clamp to raster dimensions
            valid_coords = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
            
            # Read raster array (uint8, ~1.29 GB in RAM)
            print(f"  Reading raster band into memory ({src.width}x{src.height} uint8)...", flush=True)
            band_data = src.read(1)
            
            # Sample directly via array indexing
            classes = np.zeros(count_in_tile, dtype=np.uint8)
            classes[valid_coords] = band_data[rows[valid_coords], cols[valid_coords]]
            
            del band_data # Free raster memory immediately
            
        df_fires.loc[subset_idx, "land_cover_class"] = classes
        df_fires.loc[subset_idx, "is_cropland"] = (classes == 40)
        
        # Print class distribution for this tile
        val_counts = pd.Series(classes).value_counts().to_dict()
        desc_counts = {ESA_CLASSES.get(k, f"Class {k}"): v for k, v in val_counts.items()}
        print(f"  Class distribution for {t_name}: {desc_counts}", flush=True)
        
    df_fires["year"] = pd.to_datetime(df_fires["acq_date"]).dt.year
    df_fires["state"] = df_fires["region"].str.lower()
    df_fires["land_cover_name"] = df_fires["land_cover_class"].map(lambda c: ESA_CLASSES.get(c, "Unclassified"))
    
    # Dataset B1: All fires (with real land cover attributes)
    out_b1 = OUTPUT_DIR / "punjab_haryana_fires_all_2018_2025.parquet"
    df_fires.to_parquet(out_b1, compression="snappy", index=False)
    print(f"\nSaved Enriched Dataset B1 to {out_b1} ({len(df_fires):,} records)", flush=True)
    
    # Dataset B2: Actual cropland fires (Class 40)
    df_b2 = df_fires[df_fires["is_cropland"] == True].copy()
    out_b2 = OUTPUT_DIR / "punjab_haryana_fires_cropland_2018_2025.parquet"
    df_b2.to_parquet(out_b2, compression="snappy", index=False)
    print(f"Saved Real Cropland Dataset B2 to {out_b2} ({len(df_b2):,} records)", flush=True)
    
    # Overall Land Cover Breakdown
    print("\n--- OVERALL 2018-2025 LAND COVER DISTRIBUTION AMONG ACTIVE FIRES ---", flush=True)
    overall_dist = df_fires["land_cover_name"].value_counts()
    for name, cnt in overall_dist.items():
        pct = (cnt / len(df_fires)) * 100.0
        print(f"  {name:25s}: {cnt:>8,} ({pct:5.2f}%)", flush=True)

    # Generate Annual Counts Table
    annual_rows = []
    # Raw India counts from the downloaded annual files
    raw_india_totals = {
        2018: 650470, 2019: 537746, 2020: 489632, 2021: 771938,
        2022: 591594, 2023: 579733, 2024: 552312, 2025: 646376
    }
    
    for yr in sorted(df_fires["year"].unique()):
        df_yr = df_fires[df_fires["year"] == yr]
        b1_cnt = len(df_yr)
        b2_cnt = len(df_yr[df_yr["is_cropland"] == True])
        non_crop = b1_cnt - b2_cnt
        unclass = len(df_yr[df_yr["land_cover_class"] == 0])
        punjab_cnt = len(df_yr[df_yr["state"] == "punjab"])
        haryana_cnt = len(df_yr[df_yr["state"] == "haryana"])
        ret_pct = round((b2_cnt / max(b1_cnt, 1)) * 100.0, 2)
        
        annual_rows.append({
            "year": yr,
            "india_total_raw_detections": raw_india_totals.get(yr, 0),
            "punjab_polygon_detections": punjab_cnt,
            "haryana_polygon_detections": haryana_cnt,
            "dataset_b1_total": b1_cnt,
            "dataset_b2_cropland_detected": b2_cnt,
            "non_cropland_detections": non_crop,
            "unclassified_detections": unclass,
            "cropland_retention_pct": ret_pct,
            "satellite_product": "VIIRS S-NPP 375m (VNP14IMGTDL)",
            "classification_source": "ESA WorldCover 2021 v200 (10m Resolution, Class 40)"
        })
        
    df_annual = pd.DataFrame(annual_rows)
    out_annual_csv = AUDIT_DIR / "FIRMS_ANNUAL_COUNTS.csv"
    df_annual.to_csv(out_annual_csv, index=False)
    print(f"\nSaved verified annual counts to {out_annual_csv}", flush=True)
    print(df_annual[["year", "dataset_b1_total", "dataset_b2_cropland_detected", "non_cropland_detections", "cropland_retention_pct"]])
    
    # Generate 30 Sample Fire Detections for Audit Evidence
    print("\nGenerating sample audit detections...", flush=True)
    sample_crop = df_b2.sample(20, random_state=42)
    sample_non_crop = df_fires[df_fires["is_cropland"] == False].sample(10, random_state=42)
    sample_df = pd.concat([sample_crop, sample_non_crop], ignore_index=True)
    
    cols_to_show = ["year", "acq_date", "acq_time", "latitude", "longitude", "state", "frp", "confidence", "land_cover_class", "land_cover_name", "is_cropland"]
    sample_df = sample_df[cols_to_show]
    sample_df.to_csv(AUDIT_DIR / "SAMPLE_CROPLAND_DETECTIONS.csv", index=False)
    print(f"Saved 30 sample detections to {AUDIT_DIR / 'SAMPLE_CROPLAND_DETECTIONS.csv'}", flush=True)
    
    return df_fires, df_annual, sample_df

if __name__ == "__main__":
    apply_cropland_filter()
