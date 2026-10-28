"""Master script to execute automated acquisition of the three authentic historical datasets:
1. CPCB/XKDR Delhi PM2.5 monitoring stations (2019-2024)
2. NASA FIRMS VIIRS S-NPP Active Fires in Punjab & Haryana (2019-2024)
3. ECMWF ERA5 Single-Level Reanalysis Meteorology (2019-2024)
"""

import sys
import os
import time
import json
import logging
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.acquisition.cpcb_downloader import CPCBDownloader
from src.acquisition.firms_downloader import FIRMSDownloader
from src.acquisition.era5_downloader import ERA5Downloader
from backend.app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_acquisition")

def main():
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    logger.info("=== STARTING PHASE 2: AUTOMATED DATA ACQUISITION (2019-2024) ===")
    start_time = time.time()
    
    # 1. CPCB Station Metadata & PM2.5
    logger.info("Step 1/3: Acquiring CPCB Delhi Monitoring Station PM2.5 Data...")
    cpcb = CPCBDownloader()
    stations = cpcb.fetch_all_stations()
    cpcb_path = cpcb.download_all_years(years=years)
    df_cpcb = pd.read_parquet(cpcb_path)
    logger.info(f"CPCB Acquisition Complete: {len(df_cpcb)} station-day records across {len(stations)} Delhi stations.")

    # 2. NASA FIRMS VIIRS Active Fires
    logger.info("Step 2/3: Acquiring NASA FIRMS VIIRS S-NPP Active Fire Detections...")
    firms = FIRMSDownloader()
    firms_path = firms.download_multi_year(years=years)
    df_firms = pd.read_parquet(firms_path)
    logger.info(f"FIRMS Acquisition Complete: {len(df_firms)} active fire detections in Punjab & Haryana.")

    # 3. ERA5 Atmospheric Reanalysis
    logger.info("Step 3/3: Acquiring ECMWF ERA5 Hourly Atmospheric Reanalysis...")
    era5 = ERA5Downloader()
    era5_path = era5.download_multi_year(years=years)
    df_era5 = pd.read_parquet(era5_path)
    logger.info(f"ERA5 Acquisition Complete: {len(df_era5)} hourly weather records.")

    elapsed = time.time() - start_time
    logger.info(f"=== PHASE 2 ACQUISITION FINISHED IN {elapsed:.1f}s ===")
    
    # Summary report
    summary = {
        "status": "COMPLETED",
        "study_period": "2019-2024 (September 1 to December 31, annual peak fire & pollution episodes)",
        "datasets": {
            "cpcb_delhi_pm25": {
                "source": "CPCB / XKDR India Air Quality Database",
                "stations_count": len(stations),
                "total_station_days": len(df_cpcb),
                "raw_file": str(cpcb_path),
            },
            "firms_active_fires": {
                "source": "NASA LANCE / FIRMS (VIIRS S-NPP 375m)",
                "total_fire_detections": len(df_firms),
                "regions": ["Punjab", "Haryana"],
                "raw_file": str(firms_path),
            },
            "era5_meteorology": {
                "source": "ECMWF ERA5 Reanalysis (Single Levels)",
                "total_hourly_records": len(df_era5),
                "locations": ["Delhi Centroid", "Punjab-Haryana Regional Centroid"],
                "raw_file": str(era5_path),
            }
        }
    }
    
    # Save metadata summary
    meta_summary_path = settings.DATA_METADATA_DIR / "acquisition_summary.json"
    with open(meta_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved acquisition metadata summary to {meta_summary_path}")

if __name__ == "__main__":
    main()
