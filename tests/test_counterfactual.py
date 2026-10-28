"""Tests for the model-based fire-reduction counterfactual scenarios."""

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb
from fastapi.testclient import TestClient
from sklearn.impute import SimpleImputer

from backend.app.main import app
from backend.app.services.data_service import data_service
from src.models.counterfactual import (
    SCENARIO_REDUCTIONS,
    SCALABLE_FIRE_FEATURES,
    apply_fire_reduction,
    compare_predictions,
    predict_pm25,
    simulate_fire_reduction,
)

client = TestClient(app)
DATE = "2024-11-18"


@pytest.fixture(scope="module")
def pipeline():
    """Small XGBoost model fitted on the real Exp C training rows (2018-2022)."""
    df = data_service.ml_dataset
    feats = data_service.feature_lists["exp_c_engineered_fires"]
    train = df[df["year"].between(2018, 2022)]
    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(train[feats])
    model = xgb.XGBRegressor(n_estimators=40, max_depth=3, random_state=42)
    model.fit(X_train, train["delhi_daily_pm25_ugm3"].values)
    row = df[df["date_str"] == DATE].iloc[0]
    return model, imputer, feats, row


def test_zero_reduction_matches_baseline(pipeline):
    model, imputer, feats, row = pipeline
    baseline = predict_pm25(model, imputer, None, feats, row)
    unchanged = apply_fire_reduction(row, feats, 0)
    assert predict_pm25(model, imputer, None, feats, unchanged) == baseline


def test_only_fire_inputs_change(pipeline):
    model, imputer, feats, row = pipeline
    scenario = apply_fire_reduction(row, feats, 50)
    for col in feats:
        if col in SCALABLE_FIRE_FEATURES:
            assert scenario[col] == pytest.approx(row[col] * 0.5)
        else:
            assert scenario[col] == row[col] or (pd.isna(scenario[col]) and pd.isna(row[col]))
    assert apply_fire_reduction(row, feats, 100)[SCALABLE_FIRE_FEATURES].eq(0).all()
    assert row["fire_count_total"] == 1845  # original row not mutated


def test_invalid_inputs_raise(pipeline):
    _, _, feats, row = pipeline
    with pytest.raises(ValueError):
        apply_fire_reduction(row, feats, 101)
    with pytest.raises(ValueError):
        apply_fire_reduction(row, feats, -5)
    bad_row = row.copy()
    bad_row["fire_count_total"] = np.nan
    with pytest.raises(ValueError):
        apply_fire_reduction(bad_row, feats, 25)
    with pytest.raises(ValueError):  # a fire feature we do not know how to scale
        apply_fire_reduction(row, feats + ["fire_count_total_lag1"], 25)


def test_output_calculations():
    result = compare_predictions(200.0, 150.0)
    assert result["absolute_difference"] == -50.0
    assert result["percent_difference"] == -25.0
    for bad_baseline in (0.0, -10.0, float("nan"), float("inf")):
        assert compare_predictions(bad_baseline, 100.0)["percent_difference"] is None


def test_simulation_output_structure(pipeline):
    model, imputer, feats, row = pipeline
    result = simulate_fire_reduction(model, imputer, None, feats, row)
    assert [s["fire_reduction_pct"] for s in result["scenarios"]] == SCENARIO_REDUCTIONS
    assert result["baseline_pm25"] == predict_pm25(model, imputer, None, feats, row)
    for s in result["scenarios"]:
        assert s["baseline_pm25"] == result["baseline_pm25"]
        assert s["absolute_difference"] == pytest.approx(s["scenario_pm25"] - s["baseline_pm25"])


def test_api_unknown_date_and_bad_model():
    assert client.post("/api/simulate/fire-reduction", json={"date": "1999-01-01"}).status_code == 404
    assert client.post("/api/simulate/fire-reduction", json={"date": DATE, "model_name": "nope"}).status_code == 400


def test_api_reports_missing_model_artifacts(monkeypatch):
    monkeypatch.setattr(data_service, "models", {})
    response = client.post("/api/simulate/fire-reduction", json={"date": DATE})
    assert response.status_code == 503
    assert "missing" in response.json()["detail"]


def test_api_baseline_matches_predict_endpoint():
    if "xgboost" not in data_service.models or "exp_c" not in data_service.imputers:
        pytest.skip("Trained Exp C artifacts not found in artifacts/final_models/")
    sim = client.post("/api/simulate/fire-reduction", json={"date": DATE}).json()
    pred = client.post("/api/predict", json={"mode": "historical_retrospective", "date": DATE}).json()
    assert sim["baseline_pm25"] == pytest.approx(pred["predicted_pm25"], abs=0.01)
    assert len(sim["scenarios"]) == 4
    assert "not a proven causal effect" in sim["scientific_disclaimer"]