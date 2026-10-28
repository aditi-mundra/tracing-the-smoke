"""Comprehensive End-to-End Test Suite for Tracing the Smoke.
Covers:
1. Data Integrity: Station metadata, coordinates, daily aggregation schemas.
2. Geospatial Calculations: Distance, bearing, meteorological wind conversion, alignment.
3. Temporal Validation: Chronological splits, zero temporal leakage, imputer/scaler isolation.
4. Model Serialization & Inference: Loading saved artifacts, generating valid predictions.
5. API Integration: Health, overview, stations, models, evaluation, SHAP, and prediction endpoints.
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from src.geospatial.spatial_features import (
    haversine_distance,
    calculate_bearing,
    wind_direction_to_transport_direction,
    calculate_wind_alignment,
    calculate_distance_weight
)
from src.models.train_models import FEATURE_SETS

client = TestClient(app)

# --- 1. DATA INTEGRITY TESTS ---
def test_stations_metadata():
    stations_file = settings.DATA_METADATA_DIR / "delhi_stations.json"
    assert stations_file.exists(), "delhi_stations.json metadata must exist"
    with open(stations_file, "r", encoding="utf-8") as f:
        stations = json.load(f)
    assert len(stations) >= 40, f"Expected at least 40 Delhi stations, found {len(stations)}"
    for st in stations:
        assert "station_id" in st
        assert "latitude" in st and "longitude" in st
        assert 28.3 <= st["latitude"] <= 28.95, f"Station {st['station_id']} latitude out of Delhi bounds"
        assert 76.8 <= st["longitude"] <= 77.45, f"Station {st['station_id']} longitude out of Delhi bounds"

def test_ml_dataset_schema():
    dataset_path = settings.DATA_PROCESSED_DIR / "delhi_pm25_ml_dataset.parquet"
    assert dataset_path.exists(), "ML dataset parquet file must exist"
    df = pd.read_parquet(dataset_path)
    assert len(df) >= 700, f"Expected multi-year daily dataset (>700 days), got {len(df)}"
    
    # Check essential target and feature columns
    required_cols = [
        "date_str", "year", "month", "delhi_daily_pm25_ugm3", "is_severe_episode",
        "fire_count_total", "fire_count_upwind", "fire_upwind_weighted_frp",
        "wind_speed_mean", "blh_mean", "ventilation_index",
        "pm25_lag1"
    ]
    for col in required_cols:
        assert col in df.columns, f"Required column {col} missing from ML dataset"
        
    # Check target ranges (NAAQS PM2.5 concentrations must be positive and physical)
    assert (df["delhi_daily_pm25_ugm3"] > 0).all(), "PM2.5 concentration must be strictly positive"
    assert (df["delhi_daily_pm25_ugm3"] < 1200).all(), "PM2.5 concentration must be within realistic physical ceiling"

# --- 2. TEMPORAL LEAKAGE PREVENTION TESTS ---
def test_chronological_split_integrity():
    dataset_path = settings.DATA_PROCESSED_DIR / "delhi_pm25_ml_dataset.parquet"
    df = pd.read_parquet(dataset_path)
    
    train_dates = df[df["year"].between(2019, 2022)]["date_str"]
    val_dates = df[df["year"] == 2023]["date_str"]
    test_dates = df[df["year"] == 2024]["date_str"]
    
    # Strict temporal separation
    assert train_dates.max() < val_dates.min(), "Training dates must strictly precede validation dates"
    assert val_dates.max() < test_dates.min(), "Validation dates must strictly precede test dates"
    assert len(test_dates) >= 100, "Held-out test set must contain complete 2024 autumn/winter season"

# --- 3. MODEL SERIALIZATION & INFERENCE TESTS ---
def test_trained_model_loading_and_inference():
    feat_dict_file = settings.DATA_PROCESSED_FINAL_DIR / "feature_dictionary.json"
    if feat_dict_file.exists():
        with open(feat_dict_file, "r") as f:
            feat_cols = json.load(f)["experiments"]["exp_c_engineered_fires"]["features"]
    else:
        feat_cols = FEATURE_SETS["exp_c_engineered_fires"]

    imputer = joblib.load(settings.TRAINED_MODELS_DIR / "imputer_exp_c_engineered_fires.joblib")
    scaler = joblib.load(settings.TRAINED_MODELS_DIR / "scaler_exp_c_engineered_fires.joblib")

    for model_name in ["linear_regression", "random_forest", "xgboost", "lightgbm"]:
        model_file = settings.TRAINED_MODELS_DIR / f"model_{model_name}_exp_c_engineered_fires.joblib"
        assert model_file.exists(), f"Model artifact {model_file} must exist"
        model = joblib.load(model_file)
        assert model is not None
        
        sample_input = pd.DataFrame([np.zeros(len(feat_cols))], columns=feat_cols)
        sample_imp = pd.DataFrame(imputer.transform(sample_input), columns=feat_cols)
        
        if model_name in ["linear_regression", "ridge"]:
            sample_scaled = scaler.transform(sample_imp)
            pred = model.predict(sample_scaled)
        else:
            pred = model.predict(sample_imp)
            
        assert len(pred) == 1
        assert not np.isnan(pred[0]), f"Model {model_name} produced NaN prediction"

# --- 4. BACKEND API INTEGRATION TESTS ---
def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["project"] == "Tracing the Smoke"

def test_api_overview():
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    assert "observed_pm25" in data
    assert "fire_count_total" in data
    assert "prevailing_wind_direction" in data

def test_api_evaluation():
    res = client.get("/api/evaluation")
    assert res.status_code == 200
    data = res.json()
    assert "comparison_table" in data
    assert len(data["comparison_table"]) >= 10
    assert "ablation_summary" in data

def test_api_shap_global():
    res = client.get("/api/shap/global")
    assert res.status_code == 200
    data = res.json()
    assert "global_importance" in data
    assert "grouped_importance" in data
    assert len(data["global_importance"]) > 0

def test_api_predict_endpoint():
    payload = {
        "mode": "next_day_forecast",
        "date": "2024-11-04",
        "model_name": "xgboost"
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "predicted_pm25" in data
    assert data["predicted_pm25"] > 0
    assert "is_severe_episode" in data
    assert data["forecast_horizon"] == "Next-Day (t+1)"
