"""Autonomous 24/7 Live Data Ingestion and Telemetry Synchronizer for Tracing the Smoke.
Can be executed as an automated cron task, systemd service, or background daemon.

Functions:
1. Ingests live high-resolution NWP weather & BLH from Open-Meteo for Delhi NCT.
2. Checks FIRMS active fire satellite updates for Punjab & Haryana.
3. Computes live atmospheric advection vectors and smoke plume transit time.
4. Synthesizes live station grid and evaluates GRAP early warning advisory.
5. Logs real-time operational status to data/live_stream/live_telemetry_latest.json.
"""

import sys
import json
import time
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.live_service import live_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sync_live_feed")

LIVE_DIR = PROJECT_ROOT / "data" / "live_stream"
LIVE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = LIVE_DIR / "live_telemetry_latest.json"

def sync_live():
    logger.info("=== STARTING AUTONOMOUS REAL-TIME TELEMETRY SYNC ===")
    try:
        telemetry = live_service.refresh_now()
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(telemetry, f, indent=2)
            
        logger.info(f"Successfully synced live telemetry to {OUTPUT_FILE}")
        logger.info(f"Live Delhi Weather: {telemetry['weather']['temperature_c']}°C, Wind: {telemetry['weather']['wind_speed_ms']} m/s @ {telemetry['weather']['wind_direction_deg']}°")
        logger.info(f"BLH: {telemetry['weather']['boundary_layer_height_m']}m, Ventilation: {telemetry['weather']['ventilation_index']} m²/s")
        logger.info(f"Advection Risk: {telemetry['transport_analysis']['smoke_transport_risk']}")
        logger.info(f"Live Estimated PM2.5: {telemetry['air_quality_telemetry']['live_estimated_pm25']} µg/m³ ({telemetry['air_quality_telemetry']['aqi_category']})")
        logger.info("=== SYNC COMPLETED SUCCESSFULLY ===")
        return telemetry
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return None

if __name__ == "__main__":
    sync_live()
