"""Configuration module for Tracing the Smoke backend application and ML pipelines."""

import os
from pathlib import Path
from pydantic import BaseModel

# Project Root is two levels up from backend/app
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseModel):
    PROJECT_NAME: str = "Tracing the Smoke"
    PROJECT_SUBTITLE: str = "Machine Learning Attribution of Punjab-Haryana Stubble Burning to Delhi PM2.5 Pollution"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Paths
    BASE_DIR: Path = PROJECT_ROOT
    DATA_RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
    DATA_INTERIM_DIR: Path = PROJECT_ROOT / "data" / "interim"
    DATA_PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
    DATA_PROCESSED_FINAL_DIR: Path = PROJECT_ROOT / "data" / "processed_final"
    DATA_METADATA_DIR: Path = PROJECT_ROOT / "data" / "metadata"
    ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts"
    TRAINED_MODELS_DIR: Path = ARTIFACTS_DIR / "final_models"
    EVALUATION_DIR: Path = ARTIFACTS_DIR / "final_evaluation"
    SHAP_DIR: Path = ARTIFACTS_DIR / "final_shap"
    FIGURES_DIR: Path = ARTIFACTS_DIR / "figures"
    
    # Study Constants
    DELHI_LATITUDE: float = 28.6139
    DELHI_LONGITUDE: float = 77.2090
    
    # Severe Pollution Threshold according to NAAQS / CPCB PM2.5 standards:
    # 24-hr standard: 60 ug/m3, Moderate: 61-90, Poor: 91-120, Very Poor: 121-250, Severe: > 250 ug/m3
    SEVERE_PM25_THRESHOLD: float = 250.0
    HIGH_POLLUTION_THRESHOLD: float = 120.0  # Very Poor / Severe threshold for high episode sensitivity
    
    # Historical Study Coverage Target (Full Multi-Year Foundation)
    START_YEAR: int = 2018
    END_YEAR: int = 2025
    
    # API configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

settings = Settings()
