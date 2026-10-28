"""Wind-aware Fire Transport Risk Score (relative ranking, not a dispersion model).

For every valid fire detection in Punjab/Haryana inside the lookback window:

    wind_free_score = FRP * distance_weight(distance_to_Delhi)
    transport_risk  = wind_free_score * wind_alignment

where wind_alignment = max(0, cos(bearing_fire_to_Delhi - smoke_transport_direction)),
using the same helpers as the existing feature pipeline (spatial_features.py).
Fires are grouped into ~0.5 degree grid cells (~55 km) and cell scores are summed.

What the score is NOT: it does not simulate smoke dispersion, plume rise, chemistry,
deposition or travel time, and it is not in ug/m3. It is a unitless index that says
"which fire areas are best placed, by intensity, distance and wind direction, to
matter for Delhi". Compare scores within one run only.

Lag handling: fires from `lookback_days` days before the target date up to the target
date are included with equal weight (3 days mirrors the fire_*_lag1..lag3 features in
feature_builder.py). Each fire uses the wind of its own detection date.

Missing wind: a fire with no wind value gets NaN alignment (never a default
direction). Wind-aware scores only sum fires that have wind; `wind_coverage` shows the
share of cluster FRP that had wind. If no fire has wind, clusters are ranked by
`wind_free_score` and `ranking_basis` says so.
"""

import argparse
import json
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.app.config import settings
from src.geospatial.spatial_features import (
    calculate_bearing,
    calculate_distance_weight,
    calculate_wind_alignment,
    haversine_distance,
    wind_direction_to_transport_direction,
)

VALID_STATES = {"punjab": "Punjab", "haryana": "Haryana"}
DEFAULT_LOOKBACK_DAYS = 3
DEFAULT_GRID_DEG = 0.5
MIN_DAYS_FOR_CONSTANT_CHECK = 7


def clean_fire_records(fires: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Keep rows with a valid date, finite in-range coordinates, FRP >= 0 and a
    Punjab/Haryana state. Missing FRP is dropped, not imputed. Returns (clean, n_dropped)."""
    if fires is None or len(fires) == 0:
        return pd.DataFrame(columns=["date", "latitude", "longitude", "frp", "state"]), 0

    df = fires.rename(columns={"acq_date": "date", "region": "state"}).copy()
    needed = ["date", "latitude", "longitude", "frp", "state"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Fire data is missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    for col in ["latitude", "longitude", "frp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["state"] = df["state"].astype(str).str.strip().str.lower().map(VALID_STATES)

    valid = (
        df["date"].notna()
        & np.isfinite(df["latitude"]) & df["latitude"].between(-90, 90)
        & np.isfinite(df["longitude"]) & df["longitude"].between(-180, 180)
        & np.isfinite(df["frp"]) & (df["frp"] >= 0)
        & df["state"].notna()
    )
    return df[valid].reset_index(drop=True), int((~valid).sum())


def wind_is_constant_placeholder(wind_dir_deg: pd.Series) -> bool:
    """True if a long wind series has a single repeated value (not real daily wind)."""
    values = wind_dir_deg.dropna()
    return len(values) >= MIN_DAYS_FOR_CONSTANT_CHECK and values.nunique() == 1


def prepare_wind(wind: Optional[pd.DataFrame]) -> Tuple[pd.Series, Optional[str]]:
    """Turn a table with `date` and `wind_direction_deg` (meteorological, direction the
    wind blows FROM) into a date-indexed Series. Returns (series, note). The series is
    empty, with a note, when wind is absent, malformed or a constant placeholder."""
    empty = pd.Series(dtype=float)
    if wind is None or len(wind) == 0:
        return empty, "No wind data supplied; ranking is wind-free."
    if not {"date", "wind_direction_deg"}.issubset(wind.columns):
        return empty, "Wind table needs columns date, wind_direction_deg; ranking is wind-free."

    w = pd.DataFrame({
        "date": pd.to_datetime(wind["date"], errors="coerce").dt.normalize(),
        "dir": pd.to_numeric(wind["wind_direction_deg"], errors="coerce"),
    })
    w = w[w["date"].notna() & np.isfinite(w["dir"])]
    w["dir"] = w["dir"] % 360.0
    series = w.drop_duplicates("date", keep="last").set_index("date")["dir"]
    if series.empty:
        return empty, "Wind table has no valid rows; ranking is wind-free."
    if wind_is_constant_placeholder(series):
        return empty, ("Wind direction is one constant value across all days (placeholder, "
                       "not observed wind); ignored and ranking is wind-free.")
    return series, None


def score_fires(
    fires: pd.DataFrame,
    wind_by_date: pd.Series,
    target_date,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """Per-fire scores for detections in [target_date - lookback_days, target_date]."""
    end = pd.Timestamp(target_date).normalize()
    start = end - pd.Timedelta(days=lookback_days)
    df = fires[(fires["date"] >= start) & (fires["date"] <= end)].copy()
    if df.empty:
        return df

    df["distance_km"] = haversine_distance(
        df["latitude"], df["longitude"], settings.DELHI_LATITUDE, settings.DELHI_LONGITUDE)
    df["bearing_to_delhi_deg"] = calculate_bearing(
        df["latitude"], df["longitude"], settings.DELHI_LATITUDE, settings.DELHI_LONGITUDE)
    df["wind_free_score"] = df["frp"] * calculate_distance_weight(df["distance_km"])

    wind_from_deg = df["date"].map(wind_by_date)  # NaN where no wind for that date
    transport_deg = wind_direction_to_transport_direction(wind_from_deg)
    df["wind_alignment"] = calculate_wind_alignment(df["bearing_to_delhi_deg"], transport_deg)
    df["transport_risk"] = df["wind_free_score"] * df["wind_alignment"]  # NaN if no wind
    return df


def rank_fire_clusters(
    fires: pd.DataFrame,
    wind: Optional[pd.DataFrame],
    target_date,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    grid_deg: float = DEFAULT_GRID_DEG,
) -> Tuple[pd.DataFrame, List[str]]:
    """Rank grid-cell fire clusters by transport relevance to Delhi.
    Returns (ranked clusters, notes). Never raises on bad rows or missing wind."""
    notes: List[str] = []
    clean, n_dropped = clean_fire_records(fires)
    if n_dropped:
        notes.append(f"Dropped {n_dropped} fire rows (bad date/coordinates/FRP or state not Punjab/Haryana).")

    wind_by_date, wind_note = prepare_wind(wind)
    if wind_note:
        notes.append(wind_note)

    scored = score_fires(clean, wind_by_date, target_date, lookback_days)
    if scored.empty:
        notes.append("No valid fires in the lookback window.")
        return pd.DataFrame(), notes

    scored["has_wind"] = scored["wind_alignment"].notna()
    scored["frp_with_wind"] = scored["frp"].where(scored["has_wind"], 0.0)
    scored["cell_lat"] = np.floor(scored["latitude"] / grid_deg) * grid_deg
    scored["cell_lon"] = np.floor(scored["longitude"] / grid_deg) * grid_deg

    clusters = scored.groupby(["cell_lat", "cell_lon"]).agg(
        state=("state", lambda s: s.mode().iloc[0]),
        n_fires=("frp", "size"),
        frp_total_mw=("frp", "sum"),
        centroid_lat=("latitude", "mean"),
        centroid_lon=("longitude", "mean"),
        wind_free_score=("wind_free_score", "sum"),
        wind_aware_score=("transport_risk", lambda s: s.sum() if s.notna().any() else np.nan),
        frp_with_wind=("frp_with_wind", "sum"),
    ).reset_index()

    clusters["distance_km"] = haversine_distance(
        clusters["centroid_lat"], clusters["centroid_lon"],
        settings.DELHI_LATITUDE, settings.DELHI_LONGITUDE)
    clusters["wind_coverage"] = clusters["frp_with_wind"] / clusters["frp_total_mw"].replace(0, np.nan)
    clusters = clusters.drop(columns=["frp_with_wind"])

    if clusters["wind_aware_score"].notna().any():
        basis, score_col = "wind_aware", "wind_aware_score"
        if clusters["wind_aware_score"].isna().any() or (clusters["wind_coverage"] < 1).any():
            notes.append("Some fires lack wind for their date; wind-aware scores count only fires "
                         "with wind (see wind_coverage).")
    else:
        basis, score_col = "wind_free", "wind_free_score"
        notes.append("No fire had wind data: ranked by FRP x distance weight only.")

    clusters = clusters.sort_values(score_col, ascending=False, na_position="last").reset_index(drop=True)
    clusters.insert(0, "rank", np.arange(1, len(clusters) + 1))
    total = clusters[score_col].sum()
    clusters["score_share_pct"] = 100.0 * clusters[score_col] / total if total > 0 else 0.0
    clusters["ranking_basis"] = basis
    return clusters, notes


def _read_table(path: str) -> pd.DataFrame:
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return pd.DataFrame(json.load(f))
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank Punjab/Haryana fire clusters by transport relevance to Delhi.")
    parser.add_argument("--fires", required=True, help="CSV/JSON with date, latitude, longitude, frp, state")
    parser.add_argument("--wind", help="CSV/JSON with date, wind_direction_deg (direction wind blows FROM)")
    parser.add_argument("--date", required=True, help="Target date YYYY-MM-DD")
    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    wind = _read_table(args.wind) if args.wind else None
    ranked, notes = rank_fire_clusters(_read_table(args.fires), wind, args.date, args.lookback)
    for note in notes:
        print(f"NOTE: {note}")
    if not ranked.empty:
        print(ranked.head(args.top).round(2).to_string(index=False))


if __name__ == "__main__":
    main()