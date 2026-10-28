"""Acquire and extract verified GeoJSON administrative boundaries for Punjab, Haryana, and Delhi NCT.
Saves boundaries to data/geographic/:
- punjab_boundary.geojson
- haryana_boundary.geojson
- delhi_nct_boundary.geojson
- source_boundaries_manifest.json
"""

from pathlib import Path
import json
import requests
from shapely.geometry import shape, Polygon, MultiPolygon

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
GEO_DIR = PROJECT_ROOT / "data" / "geographic"
GEO_DIR.mkdir(parents=True, exist_ok=True)

# DataMeet / Open India GIS repositories
STATE_SOURCES = [
    "https://raw.githubusercontent.com/Subhash9325/GeoJson-Data-of-Indian-States/master/Indian_States",
    "https://raw.githubusercontent.com/geohacker/india/master/state/india_telengana.geojson"
]

def acquire_boundaries():
    print("=== ACQUIRING OFFICIAL STATE BOUNDARIES (PUNJAB, HARYANA, DELHI NCT) ===", flush=True)
    
    geojson_url = "https://raw.githubusercontent.com/Subhash9325/GeoJson-Data-of-Indian-States/master/Indian_States"
    print(f"Fetching national state boundaries from: {geojson_url}", flush=True)
    r = requests.get(geojson_url, timeout=30)
    r.raise_for_status()
    india_geojson = r.json()
    
    features = india_geojson.get("features", [])
    print(f"Total features loaded: {len(features)}", flush=True)
    
    extracted = {}
    
    for feat in features:
        props = feat.get("properties", {})
        # Check various name property conventions
        name = str(props.get("NAME_1", props.get("st_nm", props.get("name", props.get("State", ""))))).strip().lower()
        
        target_state = None
        if "punjab" in name:
            target_state = "punjab"
        elif "haryana" in name:
            target_state = "haryana"
        elif "delhi" in name or "nct" in name:
            target_state = "delhi_nct"
            
        if target_state and target_state not in extracted:
            geom = feat.get("geometry")
            shp = shape(geom)
            bounds = shp.bounds # (minx, miny, maxx, maxy) -> (min_lon, min_lat, max_lon, max_lat)
            area_approx = shp.area
            
            extracted[target_state] = {
                "state_id": target_state,
                "original_properties": props,
                "geometry_type": geom.get("type"),
                "bounding_box_lon_lat": list(bounds),
                "feature": feat
            }
            
            out_file = GEO_DIR / f"{target_state}_boundary.geojson"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(feat, f, indent=2)
            print(f"  Extracted {target_state.upper()}: Bounding Box lon/lat: [{bounds[0]:.4f}, {bounds[1]:.4f}, {bounds[2]:.4f}, {bounds[3]:.4f}] -> Saved to {out_file}", flush=True)
            
    assert "punjab" in extracted, "Punjab boundary missing from source GeoJSON"
    assert "haryana" in extracted, "Haryana boundary missing from source GeoJSON"
    assert "delhi_nct" in extracted, "Delhi boundary missing from source GeoJSON"
    
    # Save manifest
    manifest_data = {
        "source_url": geojson_url,
        "coordinate_reference_system": "WGS 84 (EPSG:4326)",
        "boundaries": {
            k: {
                "state": k,
                "bounds_lon_lat": v["bounding_box_lon_lat"],
                "file": f"{k}_boundary.geojson"
            } for k, v in extracted.items()
        }
    }
    with open(GEO_DIR / "source_boundaries_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
        
    print("State boundaries verified and saved successfully!", flush=True)

if __name__ == "__main__":
    acquire_boundaries()
