"""Inspect FIRMS years and XKDR station metadata."""
import requests

def check_firms_years():
    print("Checking FIRMS VIIRS S-NPP archive availability for India across years:")
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    for y in years:
        url = f"https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{y}/viirs-snpp_{y}_India.csv"
        try:
            r = requests.head(url, timeout=10)
            cl = r.headers.get("Content-Length", "unknown")
            print(f"Year {y}: {url} -> status {r.status_code}, size: {cl} bytes")
        except Exception as e:
            print(f"Year {y}: Error {e}")

def check_firms_header():
    print("\nChecking FIRMS CSV headers...")
    url = "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/2023/viirs-snpp_2023_India.csv"
    r = requests.get(url, stream=True, timeout=10)
    lines = []
    for line in r.iter_lines():
        if line:
            lines.append(line.decode('utf-8', errors='ignore'))
        if len(lines) >= 5:
            break
    print("FIRMS Headers and first rows:")
    for l in lines:
        print(l)

def check_xkdr_stations_meta():
    print("\nInspecting XKDR station metadata details...")
    headers = {"Authorization": "Bearer aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"}
    url = "https://airquality.xkdr.org/v1/stations"
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        data = r.json().get("data", [])
        print(f"Sample station keys: {list(data[0].keys()) if data else []}")
        # Look for stations in NCR or Delhi
        for s in data[:10]:
            print(s)

if __name__ == "__main__":
    check_firms_years()
    check_firms_header()
    check_xkdr_stations_meta()
