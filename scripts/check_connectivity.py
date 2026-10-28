"""Script to test connectivity to verifiable open data sources:
1. XKDR India Air Quality Database (CPCB)
2. NASA FIRMS open country archive
3. ERA5 Reanalysis archive (Copernicus / Open-Meteo ERA5 reanalysis)
"""

import sys
import json
import requests

def test_xkdr():
    print("Testing XKDR CPCB API...")
    url = "https://api.airquality.xkdr.org/v1/stations"
    try:
        r = requests.get(url, timeout=10)
        print(f"XKDR /v1/stations status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            stations = data.get("data", [])
            print(f"Total stations found: {len(stations)}")
            delhi_stations = [s for s in stations if "delhi" in str(s.get("city", "")).lower() or "delhi" in str(s.get("state", "")).lower()]
            print(f"Delhi stations identified: {len(delhi_stations)}")
            return True, len(delhi_stations)
    except Exception as e:
        print(f"XKDR error: {e}")
    return False, 0

def test_firms():
    print("\nTesting NASA FIRMS Archive / API...")
    # Test FIRMS country archive or open sample URL
    url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/open_key/VIIRS_SNPP_NRT/73,28,78,32/1"
    try:
        r = requests.get(url, timeout=10)
        print(f"FIRMS API test status: {r.status_code}")
        print(f"Response sample (first 150 bytes): {r.text[:150]}")
    except Exception as e:
        print(f"FIRMS error: {e}")

def test_era5():
    print("\nTesting ERA5 Reanalysis endpoint...")
    # Open-Meteo historical ERA5 reanalysis for Delhi (28.6139, 77.2090)
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        "latitude=28.6139&longitude=77.2090&start_date=2023-11-01&end_date=2023-11-05&"
        "hourly=temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,boundary_layer_height"
    )
    try:
        r = requests.get(url, timeout=15)
        print(f"ERA5 Reanalysis status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            hourly = d.get("hourly", {})
            print(f"ERA5 variables retrieved: {list(hourly.keys())}")
            print(f"Time steps count: {len(hourly.get('time', []))}")
            return True
    except Exception as e:
        print(f"ERA5 error: {e}")
    return False

if __name__ == "__main__":
    test_xkdr()
    test_firms()
    test_era5()
