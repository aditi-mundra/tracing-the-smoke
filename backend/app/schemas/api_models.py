"""Pydantic schemas for backend API requests and responses."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    project: str = "Tracing the Smoke"
    environment: str = "development"

class StationInfo(BaseModel):
    station_id: str
    station_name: str
    state_name: Optional[str] = "Delhi"
    city_name: Optional[str] = "Delhi"
    latitude: float
    longitude: float
    has_pm25: bool = True

class OverviewSummary(BaseModel):
    latest_date: str
    observed_pm25: float
    predicted_pm25: Optional[float] = None
    is_severe_episode: bool
    fire_count_total: int
    fire_count_punjab: int
    fire_count_haryana: int
    fire_count_upwind: int
    wind_speed: float
    prevailing_wind_direction: float
    boundary_layer_height: float
    ventilation_index: float
    study_period: str
    total_stations: int
    model_r2_best: float

class PredictionRequest(BaseModel):
    mode: str = Field(default="historical_retrospective", description="'historical_retrospective' or 'next_day_forecast'")
    date: Optional[str] = None
    model_name: str = Field(default="xgboost", description="'xgboost', 'lightgbm', 'random_forest', 'linear_regression'")
    features: Optional[Dict[str, float]] = None

class PredictionResponse(BaseModel):
    mode: str
    model_name: str
    date: Optional[str]
    forecast_origin_date: Optional[str] = None
    target_forecast_date: Optional[str] = None
    predicted_pm25: float
    is_severe_episode: bool
    actual_pm25: Optional[float] = None
    absolute_error: Optional[float] = None
    persistence_baseline: Optional[float] = None
    forecast_horizon: str
    top_contributing_features: Optional[List[Dict[str, Any]]] = None
    scientific_disclaimer: str

class CounterfactualSimulationRequest(BaseModel):
    date: str = Field(default="2024-11-18", description="Target calendar date")
    punjab_abatement_pct: float = Field(default=50.0, ge=0.0, le=100.0, description="Punjab fire reduction percentage (0-100%)")
    haryana_abatement_pct: float = Field(default=50.0, ge=0.0, le=100.0, description="Haryana fire reduction percentage (0-100%)")
    wind_speed_multiplier: float = Field(default=1.0, ge=0.3, le=3.0, description="Wind speed multiplier (0.3 to 3.0)")
    blh_multiplier: float = Field(default=1.0, ge=0.3, le=3.0, description="Boundary layer height multiplier (0.3 to 3.0)")
    model_name: Optional[str] = "xgboost"

class CounterfactualSimulationResponse(BaseModel):
    date: str
    baseline_pm25: float
    simulated_pm25: float
    delta_pm25: float
    pct_reduction: float
    baseline_grap_stage: str
    simulated_grap_stage: str
    stage_transition: str
    avoided_severe_episode: bool
    estimated_avoided_health_impact: Dict[str, Any]
    source_attribution_breakdown: Dict[str, float]
    advisory_recommendation: str
    scientific_disclaimer: str

class FireReductionRequest(BaseModel):
    date: str = Field(description="Target calendar date (YYYY-MM-DD)")
    model_name: str = Field(default="xgboost", description="'xgboost', 'lightgbm', 'random_forest' or 'ridge'")

class FireReductionScenario(BaseModel):
    fire_reduction_pct: int
    baseline_pm25: float
    scenario_pm25: float
    absolute_difference: float
    percent_difference: Optional[float] = None

class FireReductionResponse(BaseModel):
    date: str
    model_name: str
    fire_features_scaled: List[str]
    baseline_pm25: float
    scenarios: List[FireReductionScenario]
    scientific_disclaimer: str

class FireTransportCluster(BaseModel):
    rank: int
    state: str
    n_fires: int
    frp_total_mw: float
    centroid_lat: float
    centroid_lon: float
    distance_km: float
    wind_free_score: float
    wind_aware_score: Optional[float] = None
    wind_coverage: Optional[float] = None
    score_share_pct: float
    ranking_basis: str

class FireTransportRiskResponse(BaseModel):
    target_date: str
    lookback_days: int
    ranking_basis: str
    wind_source: str
    clusters: List[FireTransportCluster]
    notes: List[str]
