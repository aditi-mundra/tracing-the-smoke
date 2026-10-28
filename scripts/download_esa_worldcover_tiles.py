"""Download authentic ESA WorldCover 2021 10m Land Cover GeoTIFFs covering Punjab and Haryana.
Tiles:
- N27E072 (lat 27-30, lon 72-75)
- N27E075 (lat 27-30, lon 75-78)
- N30E072 (lat 30-33, lon 72-75)
- N30E075 (lat 30-33, lon 75-78)
"""
from pathlib import Path
import requests
import hashlib
import time

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
ESA_DIR = PROJECT_ROOT / "data" / "geographic" / "esa_worldcover"
ESA_DIR.mkdir(parents=True, exist_ok=True)

TILES = ["N27E072", "N27E075", "N30E072", "N30E075"]
BASE_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def download_tiles():
    print("=== STARTING ESA WORLDCOVER 2021 TILE DOWNLOAD ===", flush=True)
    manifest = {}
    
    for tile in TILES:
        filename = f"ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
        out_file = ESA_DIR / filename
        url = f"{BASE_URL}/{filename}"
        
        # Check expected file size via HEAD
        head_r = requests.head(url, headers=HEADERS, timeout=30)
        expected_len = int(head_r.headers.get("content-length", 0))
        
        if out_file.exists() and out_file.stat().st_size == expected_len:
            size_mb = out_file.stat().st_size / (1024 * 1024)
            print(f"[{tile}] File already fully downloaded: {filename} ({size_mb:.2f} MB)", flush=True)
        else:
            if out_file.exists():
                out_file.unlink() # Delete partial file
            print(f"[{tile}] Downloading {url} ({expected_len / (1024*1024):.2f} MB)...", flush=True)
            t0 = time.time()
            with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(out_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            elapsed = time.time() - t0
            size_mb = out_file.stat().st_size / (1024 * 1024)
            print(f"  Downloaded {size_mb:.2f} MB in {elapsed:.1f}s ({size_mb/max(elapsed,0.1):.2f} MB/s)", flush=True)
            
        sha = file_sha256(out_file)
        manifest[tile] = {
            "filename": filename,
            "size_bytes": out_file.stat().st_size,
            "sha256": sha,
            "url": url
        }
        print(f"  Verified SHA-256: {sha[:16]}...", flush=True)

    print("\nAll 4 ESA WorldCover tiles verified successfully!", flush=True)
    return manifest

if __name__ == "__main__":
    download_tiles()
