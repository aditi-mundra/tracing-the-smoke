"""Focused API tests for relative fire-transport ranking."""

import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.services.data_service import data_service

client = TestClient(app)
TARGET_DATE = "2024-10-20"


@pytest.fixture
def sample_hotspots(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_METADATA_DIR", tmp_path)
    (tmp_path / "sample_fire_hotspots.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(data_service, "fire_hotspots", [
        {
            "date": TARGET_DATE,
            "latitude": 30.5,
            "longitude": 75.5,
            "state": "Punjab",
            "frp": 100.0,
        },
        {
            "date": "2024-10-19",
            "latitude": 30.6,
            "longitude": 75.6,
            "state": "Haryana",
            "frp": 50.0,
        },
    ])


def test_fire_transport_endpoint_returns_wind_free_ranked_clusters(sample_hotspots):
    response = client.get(
        "/api/fires/transport-risk",
        params={"date": TARGET_DATE, "lookback_days": 1},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["target_date"] == TARGET_DATE
    assert result["lookback_days"] == 1
    assert result["ranking_basis"] == "wind_free"
    assert result["wind_source"].startswith("none")
    assert any("wind-free" in note.lower() for note in result["notes"])
    assert result["clusters"]
    cluster = result["clusters"][0]
    assert cluster["rank"] == 1
    assert cluster["n_fires"] == 2
    assert cluster["distance_km"] > 0
    assert cluster["wind_coverage"] == 0
    assert cluster["ranking_basis"] == "wind_free"
    assert "wind_aware_score" in cluster


def test_fire_transport_endpoint_rejects_invalid_date(sample_hotspots):
    response = client.get("/api/fires/transport-risk", params={"date": "2024-02-30"})
    assert response.status_code == 400


def test_fire_transport_endpoint_rejects_negative_lookback(sample_hotspots):
    response = client.get(
        "/api/fires/transport-risk",
        params={"date": TARGET_DATE, "lookback_days": -1},
    )
    assert response.status_code == 422


def test_fire_transport_endpoint_reports_missing_data_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_METADATA_DIR", tmp_path)
    response = client.get("/api/fires/transport-risk", params={"date": TARGET_DATE})
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_fire_transport_endpoint_reports_no_valid_fires(sample_hotspots, monkeypatch):
    monkeypatch.setattr(data_service, "fire_hotspots", [])
    response = client.get("/api/fires/transport-risk", params={"date": TARGET_DATE})
    assert response.status_code == 404
    assert "No valid fire hotspots" in response.json()["detail"]
