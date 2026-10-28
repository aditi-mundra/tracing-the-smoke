"""Machine Learning Model Training Pipeline with Chronological Temporal Validation.
Trains and compares:
1. Baseline Persistence Model
2. Linear Regression (L2 regularized / Ridge)
3. Random Forest Regressor
4. XGBoost Regressor
5. LightGBM Regressor

Enforces strict chronological splitting to prevent temporal data leakage:
- Train: 2019 - 2022
- Validation: 2023
- Test: 2024 (held-out out-of-time evaluation)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import xgboost as xgb
import lightgbm as lgb

from backend.app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_models")

# Feature sets definition
FEATURE_SETS = {
    # Experiment A: Meteorology + Inversion + Calendar + Prior Pollution (No Fire Features)
    "exp_a_baseline": [
        "temp_mean", "temp_min", "rh_mean", "dew_point_mean", "surface_pressure_mean",
        "wind_speed_mean", "wind_speed_max", "u_wind_mean", "v_wind_mean",
        "blh_mean", "blh_min", "ventilation_index",
        "month", "doy_sin", "doy_cos", "is_weekend",
        "pm25_lag1", "pm25_lag2", "pm25_rolling_3d", "pm25_rolling_7d"
    ],
    # Experiment B: Baseline + Basic Regional Fire Counts
    "exp_b_basic_fires": [
        "temp_mean", "temp_min", "rh_mean", "dew_point_mean", "surface_pressure_mean",
        "wind_speed_mean", "wind_speed_max", "u_wind_mean", "v_wind_mean",
        "blh_mean", "blh_min", "ventilation_index",
        "month", "doy_sin", "doy_cos", "is_weekend",
        "pm25_lag1", "pm25_lag2", "pm25_rolling_3d", "pm25_rolling_7d",
        "fire_count_total", "fire_count_punjab", "fire_count_haryana", "fire_frp_total", "fire_frp_mean"
    ],
    # Experiment C: Baseline + Wind-Aligned, Distance-Weighted, Upwind-FRP and Fire Lags
    "exp_c_engineered_fires": [
        "temp_mean", "temp_min", "rh_mean", "dew_point_mean", "surface_pressure_mean",
        "wind_speed_mean", "wind_speed_max", "u_wind_mean", "v_wind_mean",
        "blh_mean", "blh_min", "ventilation_index",
        "month", "doy_sin", "doy_cos", "is_weekend",
        "pm25_lag1", "pm25_lag2", "pm25_rolling_3d", "pm25_rolling_7d",
        "fire_count_total", "fire_count_punjab", "fire_count_haryana",
        "fire_count_upwind", "fire_upwind_weighted_frp", "fire_distance_weighted_count",
        "fire_distance_mean_km", "fire_count_near_150km", "fire_count_mid_150_300km",
        "fire_upwind_weighted_frp_lag1", "fire_upwind_weighted_frp_lag2", "fire_upwind_rolling_3d"
    ]
}

TARGET_COL = "delhi_daily_pm25_ugm3"

class ModelTrainer:
    def __init__(
        self,
        dataset_path: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None
    ):
        self.dataset_path = dataset_path or settings.DATA_PROCESSED_DIR / "delhi_pm25_ml_dataset.parquet"
        self.models_dir = (artifacts_dir or settings.TRAINED_MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
    def load_and_split(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Chronologically split dataset into Train (2019-2022), Validation (2023), and Test (2024)."""
        logger.info(f"Loading ML dataset from {self.dataset_path}...")
        df = pd.read_parquet(self.dataset_path)
        df["date"] = pd.to_datetime(df["date_str"])
        df = df.sort_values("date").reset_index(drop=True)
        
        train_df = df[df["year"].between(2019, 2022)].copy()
        val_df = df[df["year"] == 2023].copy()
        test_df = df[df["year"] == 2024].copy()
        
        logger.info(
            f"Temporal Split: Train={len(train_df)} days (2019-2022), "
            f"Val={len(val_df)} days (2023), Test={len(test_df)} days (2024)"
        )
        return train_df, val_df, test_df

    def train_models_for_experiment(
        self,
        exp_name: str,
        feature_cols: List[str],
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Train all 4 algorithms plus baseline on the specified feature set."""
        logger.info(f"--- Training Models for Experiment: {exp_name} ({len(feature_cols)} features) ---")
        
        X_train = train_df[feature_cols].copy()
        y_train = train_df[TARGET_COL].values
        
        X_val = val_df[feature_cols].copy()
        y_val = val_df[TARGET_COL].values
        
        X_test = test_df[feature_cols].copy()
        y_test = test_df[TARGET_COL].values
        
        # Fit imputer and scaler strictly on training data to prevent temporal leakage
        imputer = SimpleImputer(strategy="median")
        X_train_imp = pd.DataFrame(imputer.fit_transform(X_train), columns=feature_cols)
        X_val_imp = pd.DataFrame(imputer.transform(X_val), columns=feature_cols)
        X_test_imp = pd.DataFrame(imputer.transform(X_test), columns=feature_cols)
        
        imputer_path = self.models_dir / f"imputer_{exp_name}.joblib"
        joblib.dump(imputer, imputer_path)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imp)
        X_val_scaled = scaler.transform(X_val_imp)
        X_test_scaled = scaler.transform(X_test_imp)
        
        # Save scaler
        scaler_path = self.models_dir / f"scaler_{exp_name}.joblib"
        joblib.dump(scaler, scaler_path)
        
        models = {}
        
        # 1. Baseline Model (Predicts previous-day PM2.5, i.e. persistence)
        models["baseline_persistence"] = {
            "type": "baseline",
            "feature_cols": feature_cols,
            "train_pred": train_df["pm25_lag1"].values,
            "val_pred": val_df["pm25_lag1"].values,
            "test_pred": test_df["pm25_lag1"].values,
        }
        
        # 2. Linear Regression (Ridge)
        lr = Ridge(alpha=10.0, random_state=42)
        lr.fit(X_train_scaled, y_train)
        models["linear_regression"] = {
            "model": lr,
            "scaler": scaler,
            "feature_cols": feature_cols,
            "train_pred": lr.predict(X_train_scaled),
            "val_pred": lr.predict(X_val_scaled),
            "test_pred": lr.predict(X_test_scaled),
        }
        joblib.dump(lr, self.models_dir / f"model_linear_regression_{exp_name}.joblib")
        
        # 3. Random Forest Regressor
        rf = RandomForestRegressor(
            n_estimators=150,
            max_depth=10,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X_train_imp, y_train)
        models["random_forest"] = {
            "model": rf,
            "feature_cols": feature_cols,
            "train_pred": rf.predict(X_train_imp),
            "val_pred": rf.predict(X_val_imp),
            "test_pred": rf.predict(X_test_imp),
        }
        joblib.dump(rf, self.models_dir / f"model_random_forest_{exp_name}.joblib")
        
        # 4. XGBoost Regressor
        xgb_model = xgb.XGBRegressor(
            n_estimators=180,
            learning_rate=0.04,
            max_depth=5,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.5,
            reg_lambda=1.5,
            random_state=42,
            n_jobs=-1
        )
        xgb_model.fit(
            X_train_imp, y_train,
            eval_set=[(X_val_imp, y_val)],
            verbose=False
        )
        models["xgboost"] = {
            "model": xgb_model,
            "feature_cols": feature_cols,
            "train_pred": xgb_model.predict(X_train_imp),
            "val_pred": xgb_model.predict(X_val_imp),
            "test_pred": xgb_model.predict(X_test_imp),
        }
        joblib.dump(xgb_model, self.models_dir / f"model_xgboost_{exp_name}.joblib")
        
        # 5. LightGBM Regressor
        lgb_model = lgb.LGBMRegressor(
            n_estimators=160,
            learning_rate=0.04,
            max_depth=5,
            num_leaves=25,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.5,
            reg_lambda=1.5,
            random_state=42,
            verbose=-1
        )
        lgb_model.fit(
            X_train_imp, y_train,
            eval_set=[(X_val_imp, y_val)]
        )
        models["lightgbm"] = {
            "model": lgb_model,
            "feature_cols": feature_cols,
            "train_pred": lgb_model.predict(X_train_imp),
            "val_pred": lgb_model.predict(X_val_imp),
            "test_pred": lgb_model.predict(X_test_imp),
        }
        joblib.dump(lgb_model, self.models_dir / f"model_lightgbm_{exp_name}.joblib")
        
        logger.info(f"Completed model training for {exp_name}.")
        return models

    def train_all_experiments(self) -> Dict[str, Any]:
        """Execute full training across all 3 experimental feature sets."""
        train_df, val_df, test_df = self.load_and_split()
        all_results = {}
        for exp_name, feat_cols in FEATURE_SETS.items():
            all_results[exp_name] = self.train_models_for_experiment(
                exp_name, feat_cols, train_df, val_df, test_df
            )
        return all_results

if __name__ == "__main__":
    pass
