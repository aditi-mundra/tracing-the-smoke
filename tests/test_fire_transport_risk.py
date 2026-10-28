"""Focused tests for the wind-aware fire transport risk score."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.geospatial.fire_transport_risk import (
    clean_fire_records,
    prepare_wind,
    rank_fire_clusters,
)

DAY = "2024-10-20"


def fire(lat, lon, frp=100.0, date=DAY, state="Punjab"):
    return {"date": date, "latitude": lat, "longitude": lon, "frp": frp, "state": state}


def wind(direction, date=DAY):
    return pd.DataFrame({"date": [date], "wind_direction_deg": [direction]})


def test_invalid_rows_are_dropped_not_imputed():
    rows = pd.DataFrame([
        fire(30.5, 75.5),
        fire(95.0, 75.5),            # latitude out of range
        fire(np.nan, 75.5),          # missing latitude
        fire(30.5, 75.5, frp=np.nan),  # missing FRP
        fire(30.5, 75.5, frp=-4),    # negative FRP
        fire(30.5, 75.5, state="Rajasthan"),
        fire(30.5, 75.5, date="not-a-date"),
    ])
    clean, n_dropped = clean_fire_records(rows)
    assert len(clean) == 1 and n_dropped == 6


def test_wind_from_northwest_beats_wind_from_southeast():
    fires = pd.DataFrame([fire(30.5, 75.5)])  # NW of Delhi
    toward, _ = rank_fire_clusters(fires, wind(315.0), DAY)  # wind from NW carries smoke to Delhi
    away, _ = rank_fire_clusters(fires, wind(135.0), DAY)    # wind from SE carries smoke away
    assert toward["wind_aware_score"].iloc[0] > 0
    assert away["wind_aware_score"].iloc[0] == pytest.approx(0.0)


def test_closer_fire_scores_higher_with_same_frp_and_wind():
    fires = pd.DataFrame([fire(29.4, 76.5), fire(31.5, 74.9)])  # ~110 km vs ~420 km
    ranked, _ = rank_fire_clusters(fires, wind(315.0), DAY)
    assert ranked.loc[0, "distance_km"] < ranked.loc[1, "distance_km"]
    assert ranked.loc[0, "rank"] == 1


def test_missing_wind_falls_back_to_wind_free_without_crashing():
    fires = pd.DataFrame([fire(29.4, 76.5, frp=50), fire(31.5, 74.9, frp=500)])
    for no_wind in (None, pd.DataFrame(), wind(np.nan)):
        ranked, notes = rank_fire_clusters(fires, no_wind, DAY)
        assert (ranked["ranking_basis"] == "wind_free").all()
        assert ranked["wind_aware_score"].isna().all()
        assert any("wind" in n.lower() for n in notes)


def test_partial_wind_reports_coverage():
    fires = pd.DataFrame([fire(30.5, 75.5, date=DAY), fire(30.5, 75.5, date="2024-10-19")])
    ranked, _ = rank_fire_clusters(fires, wind(315.0, DAY), DAY)  # no wind for the 19th
    assert ranked.loc[0, "wind_coverage"] == pytest.approx(0.5)


def test_constant_wind_series_is_rejected_as_placeholder():
    days = pd.date_range("2024-10-01", periods=30)
    placeholder = pd.DataFrame({"date": days, "wind_direction_deg": 315.0})
    series, note = prepare_wind(placeholder)
    assert series.empty and "placeholder" in note


def test_lookback_window_excludes_old_and_future_fires():
    fires = pd.DataFrame([
        fire(30.5, 75.5, date="2024-10-10"),  # too old
        fire(30.5, 75.5, date="2024-10-25"),  # after target date
    ])
    ranked, notes = rank_fire_clusters(fires, wind(315.0), DAY)
    assert ranked.empty and any("No valid fires" in n for n in notes)


def test_repo_daily_wind_column_is_flagged_as_placeholder():
    path = Path("data/processed_final/delhi_pm25_ml_dataset_final.parquet")
    if not path.exists():
        pytest.skip("processed dataset not available")
    df = pd.read_parquet(path, columns=["date_str", "prevailing_wind_direction_deg"])
    series, note = prepare_wind(df.rename(columns={
        "date_str": "date", "prevailing_wind_direction_deg": "wind_direction_deg"}))
    if df["prevailing_wind_direction_deg"].nunique() == 1:
        assert series.empty and note