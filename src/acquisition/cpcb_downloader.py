"""Automated CPCB / XKDR Air Quality Data Downloader for Delhi PM2.5.
Acquires daily station-level PM2.5 measurements from all verified CAAQM monitoring stations in Delhi.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import requests

from backend.app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cpcb_downloader")

XKDR_BASE_URL = "https://airquality.xkdr.org/v1"
DEMO_BEARER = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"

class CPCBDownloader:
    def __init__(self, output_dir: Optional[Path] = None, token: Optional[str] = None):
        self.output_dir = output_dir or settings.DATA_RAW_DIR / "cpcb"
        self.metadata_dir = settings.DATA_METADATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.token = token or DEMO_BEARER
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def fetch_all_stations(self) -> List[Dict]:
        """Fetch station directory and discover all eligible Delhi continuous monitoring stations."""
        logger.info("Discovering monitoring stations from XKDR CPCB endpoint...")
        url = f"{XKDR_BASE_URL}/stations"
        r = requests.get(url, headers=self.headers, timeout=20)
        r.raise_for_status()
        stations = r.json().get("data", [])
        
        # Filter strictly for Delhi stations using verified geographic boundaries & city/state names
        # Delhi bounds: lat [28.40, 28.88], lon [76.84, 77.35]
        delhi_stations = []
        for s in stations:
            state = str(s.get("state_name", "")).lower()
            city = str(s.get("city_name", "")).lower()
            name = str(s.get("station_name", "")).lower()
            lat = s.get("latitude")
            lon = s.get("longitude")
            
            is_delhi_name = ("delhi" in state) or ("delhi" in city) or ("delhi" in name)
            is_delhi_geo = (lat is not None and lon is not None and 
                            28.38 <= lat <= 28.92 and 76.80 <= lon <= 77.40)
            
            if is_delhi_name or is_delhi_geo:
                s_copy = dict(s)
                s_copy["has_pm25"] = "PM2.5" in s.get("parameters", [])
                delhi_stations.append(s_copy)
                
        logger.info(f"Discovered {len(delhi_stations)} eligible Delhi stations.")
        
        # Save metadata
        meta_file = self.metadata_dir / "delhi_stations.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(delhi_stations, f, indent=2)
            
        # Also save stations CSV
        df_meta = pd.DataFrame(delhi_stations)
        df_meta.to_csv(self.metadata_dir / "delhi_stations.csv", index=False)
        logger.info(f"Saved station metadata to {meta_file} and csv.")
        return delhi_stations

    def download_delhi_pm25_period(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Download daily PM2.5 measurements for all Delhi stations for a given date range."""
        logger.info(f"Requesting Delhi daily PM2.5 from {start_date} to {end_date}...")
        url = (
            f"{XKDR_BASE_URL}/measurements?"
            f"city=Delhi&parameter=PM2.5&start={start_date}&end={end_date}&agg=daily&format=json"
        )
        r = requests.get(url, headers=self.headers, timeout=40)
        r.raise_for_status()
        data = r.json().get("data", [])
        logger.info(f"Retrieved {len(data)} measurement records.")
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def download_all_years(self, years: List[int], months: Optional[List[int]] = None) -> Path:
        """Download multi-year historical PM2.5 observations across all Delhi monitoring stations.
        Focuses on September 1 to December 31 across all years (stubble burning and winter pollution season),
        plus additional baseline months.
        """
        all_dfs = []
        for year in years:
            # Stubble burning & winter peak: Sep 1 to Dec 31
            start = f"{year}-09-01"
            end = f"{year}-12-31"
            logger.info(f"--- Fetching Delhi PM2.5 for season: {start} to {end} ---")
            try:
                df = self.download_delhi_pm25_period(start, end)
                if not df.empty:
                    df["year"] = year
                    all_dfs.append(df)
            except Exception as e:
                logger.error(f"Failed to fetch year {year}: {e}")
                
        if not all_dfs:
            raise RuntimeError("No PM2.5 measurements could be acquired.")
            
        combined = pd.concat(all_dfs, ignore_index=True)
        raw_output_path = self.output_dir / "delhi_cpcb_pm25_daily_raw.parquet"
        combined.to_parquet(raw_output_path, index=False)
        combined.to_csv(self.output_dir / "delhi_cpcb_pm25_daily_raw.csv", index=False)
        logger.info(f"Successfully saved {len(combined)} daily station PM2.5 records to {raw_output_path}")
        return raw_output_path

if __name__ == "__main__":
    downloader = CPCBDownloader()
    downloader.fetch_all_stations()
    downloader.download_all_years(years=[2019, 2020, 2021, 2022, 2023, 2024])
