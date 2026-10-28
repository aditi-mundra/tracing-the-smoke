"""Test script for live data sources."""
import requests

def test_xkdr_live():
    print("Testing XKDR API with bearer token...")
    headers = {"Authorization": "Bearer aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"}
    url = "https://airquality.xkdr.org/v1/stations"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            stations = data.get("data", [])
            print(f"Total stations: {len(stations)}")
            delhi_stations = [s for s in stations if "delhi" in str(s.get("city", "")).lower() or "delhi" in str(s.get("state", "")).lower()]
            print(f"Delhi stations: {len(delhi_stations)}")
            if delhi_stations:
                print(f"Sample station: {delhi_stations[0]}")
    except Exception as e:
        print(f"Error: {e}")

def test_xkdr_measurements():
    print("\nTesting XKDR PM2.5 measurements...")
    headers = {"Authorization": "Bearer aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"}
    url = "https://airquality.xkdr.org/v1/measurements?city=Delhi&parameter=PM2.5&start=2024-10-01&end=2024-11-15&agg=daily&format=json"
    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"Measurements status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            rows = d.get("data", [])
            print(f"Retrieved {len(rows)} daily Delhi station measurements")
            if rows:
                print(f"Sample measurement row: {rows[0]}")
    except Exception as e:
        print(f"Error: {e}")

def test_firms_urls():
    print("\nTesting FIRMS country archive links...")
    candidates = [
        "https://firms.modaps.eosdis.nasa.gov/country/zips/viirs-snpp_2023_India.zip",
        "https://firms.modaps.eosdis.nasa.gov/country/zips/modis_2023_India.zip",
        "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/2023/viirs-snpp_2023_India.csv",
        "https://firms.modaps.eosdis.nasa.gov/api/country/csv/open_key/VIIRS_SNPP_NRT/IND/1"
    ]
    for url in candidates:
        try:
            r = requests.head(url, timeout=10, allow_redirects=True)
            print(f"{url} -> status {r.status_code}")
        except Exception as e:
            print(f"{url} -> Error: {e}")

if __name__ == "__main__":
    test_xkdr_live()
    test_xkdr_measurements()
    test_firms_urls()
