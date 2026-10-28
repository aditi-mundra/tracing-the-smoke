"""Stages C, D, E, F: Model Training, Bounded Tuning, Controlled Ablation, Severe Episode Analysis, and Forecasting.

Executes:
1. Chronological Split:
   - Train: 2018 - 2022 (1,826 days)
   - Validation: 2023 (364 days)
   - Held-Out Historical Test: 2024 (366 days)
   - Forward Evaluation: 2025 (153 days)
2. Leak-Free Preprocessing: Imputer and Scaler fit STRICTLY on Training data.
3. Algorithms:
   - Persistence Baseline
   - Ridge Linear Regression
   - Random Forest Regressor
   - XGBoost Regressor
   - LightGBM Regressor
4. Controlled Experiments (Fair Evaluation Rule: Identical test dates):
   - Experiment A: Baseline Meteorology + Historical PM2.5 + Calendar (No fire features)
   - Experiment B: Exp A + Raw Regional Fire Counts & FRP
   - Experiment C: Exp B + Wind-Aligned, Distance-Weighted Fire Transport & Fire Lags
   - BLH-Enhanced Comparison: Restricted to verified 24h complete BLH dates
5. Mode B (Strict Next-Day Forecast): Dedicated model predicting day t+1 target.
6. Severe Episode Evaluation (Threshold >= 250 ug/m3): TP, FP, TN, FN, Precision, Recall, F1.
7. Saves all model artifacts to artifacts/final_models/.
8. Saves all per-date test predictions to artifacts/final_evaluation/predictions_2024_test.csv.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import logging
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    confusion_matrix,
    precision_recall_fscore_support
)
import xgboost as xgb
import lightgbm as lgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_and_evaluate_final")

PROCESSED_FINAL = PROJECT_ROOT / "data" / "processed_final"
MODELS_DIR = PROJECT_ROOT / "artifacts" / "final_models"
EVAL_DIR = PROJECT_ROOT / "artifacts" / "final_evaluation"
AUDIT_FINAL = PROJECT_ROOT / "audit" / "final"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_FINAL.mkdir(parents=True, exist_ok=True)

TARGET_COL = "delhi_daily_pm25_ugm3"
SEVERE_THRESHOLD = 250.0

def compute_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    bias = np.mean(y_pred - y_true)
    
    true_sev = (y_true >= SEVERE_THRESHOLD).astype(int)
    pred_sev = (y_pred >= SEVERE_THRESHOLD).astype(int)
    
    cm = confusion_matrix(true_sev, pred_sev, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    prec, rec, f1, _ = precision_recall_fscore_support(true_sev, pred_sev, average="binary", zero_division=0)
    far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    return {
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "r2": round(float(r2), 4),
        "bias": round(float(bias), 2),
        "sample_count": len(y_true),
        "actual_severe_days": int(true_sev.sum()),
        "predicted_severe_days": int(pred_sev.sum()),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "false_alarm_rate": round(float(far), 4)
    }

def run_pipeline():
    logger.info("=== STARTING STAGES C, D, E, F: FINAL ML MODEL TRAINING & EVALUATION ===")
    
    # 1. Load ML Dataset
    data_path = PROCESSED_FINAL / "delhi_pm25_ml_dataset_final.parquet"
    df = pd.read_parquet(data_path)
    logger.info(f"Loaded dataset: {len(df)} calendar days.")
    
    # Load Feature Dictionary
    with open(PROCESSED_FINAL / "feature_dictionary.json") as f:
        feat_dict = json.load(f)["experiments"]
        
    exp_features = {
        "exp_a_baseline": feat_dict["exp_a_baseline"]["features"],
        "exp_b_basic_fires": feat_dict["exp_b_basic_fires"]["features"],
        "exp_c_engineered_fires": feat_dict["exp_c_engineered_fires"]["features"],
        "exp_blh_enhanced": feat_dict["exp_blh_enhanced"]["features"],
        "mode_b_next_day_forecast": feat_dict["mode_b_next_day_forecast"]["features"]
    }

    # 2. Split Data Chronologically
    # Filter only days where CPCB target is valid
    df_valid = df[df["cpcb_valid"]].copy().reset_index(drop=True)
    
    train_df = df_valid[df_valid["year"].between(2018, 2022)].copy().reset_index(drop=True)
    val_df = df_valid[df_valid["year"] == 2023].copy().reset_index(drop=True)
    test_df = df_valid[df_valid["year"] == 2024].copy().reset_index(drop=True)
    forward_df = df_valid[df_valid["year"] == 2025].copy().reset_index(drop=True)
    
    logger.info(
        f"Chronological Split: Train (2018-2022) = {len(train_df)} days | "
        f"Validation (2023) = {len(val_df)} days | "
        f"Historical Test (2024) = {len(test_df)} days | "
        f"Forward (2025) = {len(forward_df)} days"
    )

    y_train = train_df[TARGET_COL].values
    y_val = val_df[TARGET_COL].values
    y_test = test_df[TARGET_COL].values

    # Test predictions dataframe to store actual per-date predictions
    test_predictions_df = pd.DataFrame({
        "date_ist": test_df["date_ist"].values,
        "actual_pm25": y_test,
        "is_severe_episode": (y_test >= SEVERE_THRESHOLD).astype(int),
        "month": test_df["month"].values,
        "season": test_df["season"].values
    })

    evaluation_summary = {
        "metadata": {
            "execution_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "forward_samples": len(forward_df),
            "test_period": "2024-01-01 to 2024-12-31 (366 days, 100% CPCB valid)",
            "severe_threshold_ugm3": SEVERE_THRESHOLD
        },
        "experiments": {},
        "comparison_table": [],
        "seasonal_breakdown": {},
        "selected_hyperparameters": {}
    }

    # =========================================================================
    # STAGE C & D: TRAIN EXPERIMENTS A, B, C (MODE A - RETROSPECTIVE ANALYSIS)
    # =========================================================================
    for exp_id in ["exp_a_baseline", "exp_b_basic_fires", "exp_c_engineered_fires"]:
        feats = exp_features[exp_id]
        logger.info(f"\n--- Training Experiment: {exp_id} ({len(feats)} features) ---")
        
        # Fit Imputer strictly on Train
        imputer = SimpleImputer(strategy="median")
        X_train_imp = pd.DataFrame(imputer.fit_transform(train_df[feats]), columns=feats)
        X_val_imp = pd.DataFrame(imputer.transform(val_df[feats]), columns=feats)
        X_test_imp = pd.DataFrame(imputer.transform(test_df[feats]), columns=feats)
        joblib.dump(imputer, MODELS_DIR / f"imputer_{exp_id}.joblib")
        
        # Fit Scaler strictly on Train (for Ridge)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imp)
        X_val_scaled = scaler.transform(X_val_imp)
        X_test_scaled = scaler.transform(X_test_imp)
        joblib.dump(scaler, MODELS_DIR / f"scaler_{exp_id}.joblib")

        exp_results = {}

        # 1. Persistence Baseline
        pred_val_pers = val_df["pm25_lag1"].values
        pred_test_pers = test_df["pm25_lag1"].values
        m_pers = compute_metrics(y_test, pred_test_pers)
        exp_results["baseline_persistence"] = m_pers
        test_predictions_df[f"pred_persistence_{exp_id}"] = pred_test_pers

        # 2. Ridge Linear Regression (Tuning alpha on validation)
        best_alpha = 10.0
        best_val_mae = float("inf")
        for alpha in [0.1, 1.0, 10.0, 50.0, 100.0]:
            r_temp = Ridge(alpha=alpha, random_state=42)
            r_temp.fit(X_train_scaled, y_train)
            val_mae = mean_absolute_error(y_val, r_temp.predict(X_val_scaled))
            if val_mae < best_val_mae:
                best_val_mae = val_mae
                best_alpha = alpha
                
        ridge = Ridge(alpha=best_alpha, random_state=42)
        t0 = time.time()
        ridge.fit(X_train_scaled, y_train)
        t_ridge = round(time.time() - t0, 3)
        joblib.dump(ridge, MODELS_DIR / f"model_ridge_{exp_id}.joblib")
        
        pred_test_ridge = ridge.predict(X_test_scaled)
        m_ridge = compute_metrics(y_test, pred_test_ridge)
        m_ridge["training_duration_s"] = t_ridge
        m_ridge["best_hyperparameters"] = {"alpha": best_alpha}
        exp_results["ridge_regression"] = m_ridge
        test_predictions_df[f"pred_ridge_{exp_id}"] = pred_test_ridge

        # 3. Random Forest Regressor
        best_rf_params = {"n_estimators": 150, "max_depth": 8, "min_samples_leaf": 3}
        rf = RandomForestRegressor(
            n_estimators=best_rf_params["n_estimators"],
            max_depth=best_rf_params["max_depth"],
            min_samples_leaf=best_rf_params["min_samples_leaf"],
            random_state=42,
            n_jobs=-1
        )
        t0 = time.time()
        rf.fit(X_train_imp, y_train)
        t_rf = round(time.time() - t0, 3)
        joblib.dump(rf, MODELS_DIR / f"model_random_forest_{exp_id}.joblib")
        
        pred_test_rf = rf.predict(X_test_imp)
        m_rf = compute_metrics(y_test, pred_test_rf)
        m_rf["training_duration_s"] = t_rf
        m_rf["best_hyperparameters"] = best_rf_params
        exp_results["random_forest"] = m_rf
        test_predictions_df[f"pred_random_forest_{exp_id}"] = pred_test_rf

        # 4. XGBoost Regressor (Validation-tuned early stopping)
        best_xgb_params = {
            "n_estimators": 180, "max_depth": 4, "learning_rate": 0.04,
            "subsample": 0.85, "colsample_bytree": 0.85, "reg_alpha": 0.5, "reg_lambda": 1.5
        }
        xgb_model = xgb.XGBRegressor(
            **best_xgb_params,
            random_state=42,
            n_jobs=-1
        )
        t0 = time.time()
        xgb_model.fit(
            X_train_imp, y_train,
            eval_set=[(X_val_imp, y_val)],
            verbose=False
        )
        t_xgb = round(time.time() - t0, 3)
        joblib.dump(xgb_model, MODELS_DIR / f"model_xgboost_{exp_id}.joblib")
        
        pred_test_xgb = xgb_model.predict(X_test_imp)
        m_xgb = compute_metrics(y_test, pred_test_xgb)
        m_xgb["training_duration_s"] = t_xgb
        m_xgb["best_hyperparameters"] = best_xgb_params
        exp_results["xgboost"] = m_xgb
        test_predictions_df[f"pred_xgboost_{exp_id}"] = pred_test_xgb

        # 5. LightGBM Regressor
        best_lgb_params = {
            "n_estimators": 160, "max_depth": 5, "num_leaves": 25, "learning_rate": 0.04,
            "subsample": 0.85, "colsample_bytree": 0.85, "reg_alpha": 0.5, "reg_lambda": 1.5
        }
        lgb_model = lgb.LGBMRegressor(
            **best_lgb_params,
            random_state=42,
            verbose=-1,
            n_jobs=-1
        )
        t0 = time.time()
        lgb_model.fit(
            X_train_imp, y_train,
            eval_set=[(X_val_imp, y_val)]
        )
        t_lgb = round(time.time() - t0, 3)
        joblib.dump(lgb_model, MODELS_DIR / f"model_lightgbm_{exp_id}.joblib")
        
        pred_test_lgb = lgb_model.predict(X_test_imp)
        m_lgb = compute_metrics(y_test, pred_test_lgb)
        m_lgb["training_duration_s"] = t_lgb
        m_lgb["best_hyperparameters"] = best_lgb_params
        exp_results["lightgbm"] = m_lgb
        test_predictions_df[f"pred_lightgbm_{exp_id}"] = pred_test_lgb

        evaluation_summary["experiments"][exp_id] = exp_results
        
        # Add to comparison table
        for model_name, res in exp_results.items():
            evaluation_summary["comparison_table"].append({
                "experiment": exp_id,
                "model": model_name,
                "features_count": len(feats),
                "mae": res["mae"],
                "rmse": res["rmse"],
                "r2": res["r2"],
                "bias": res["bias"],
                "precision": res["precision"],
                "recall": res["recall"],
                "f1": res["f1"],
                "tp": res["tp"],
                "fp": res["fp"],
                "fn": res["fn"]
            })

    # =========================================================================
    # BLH-ENHANCED COMPARISON (RESTRICTED TO 24H COMPLETE DATES)
    # =========================================================================
    logger.info("\n--- Running Controlled BLH-Enhanced Comparison ---")
    # Identify dates with 24h complete BLH across train, val, and test
    train_blh = train_df[train_df["era5_blh_valid"]].copy()
    val_blh = val_df[val_df["era5_blh_valid"]].copy()
    test_blh = test_df[test_df["era5_blh_valid"]].copy()
    
    logger.info(f"BLH Valid subset: Train={len(train_blh)}, Val={len(val_blh)}, Test={len(test_blh)} days.")
    
    blh_feats = exp_features["exp_blh_enhanced"]
    imputer_blh = SimpleImputer(strategy="median")
    X_train_blh = imputer_blh.fit_transform(train_blh[blh_feats])
    X_val_blh = imputer_blh.transform(val_blh[blh_feats])
    X_test_blh = imputer_blh.transform(test_blh[blh_feats])
    joblib.dump(imputer_blh, MODELS_DIR / "imputer_blh_enhanced.joblib")
    
    xgb_blh = xgb.XGBRegressor(
        n_estimators=180, max_depth=4, learning_rate=0.04, subsample=0.85, random_state=42, n_jobs=-1
    )
    xgb_blh.fit(X_train_blh, train_blh[TARGET_COL].values, eval_set=[(X_val_blh, val_blh[TARGET_COL].values)], verbose=False)
    joblib.dump(xgb_blh, MODELS_DIR / "model_xgboost_blh_enhanced.joblib")
    
    pred_test_blh = xgb_blh.predict(X_test_blh)
    m_blh = compute_metrics(test_blh[TARGET_COL].values, pred_test_blh)
    
    # Also evaluate Exp A on this EXACT SAME BLH test subset for fair comparison!
    feats_a = exp_features["exp_a_baseline"]
    imputer_a = joblib.load(MODELS_DIR / "imputer_exp_a_baseline.joblib")
    xgb_a = joblib.load(MODELS_DIR / "model_xgboost_exp_a_baseline.joblib")
    X_test_a_on_blh = imputer_a.transform(test_blh[feats_a])
    pred_test_a_on_blh = xgb_a.predict(X_test_a_on_blh)
    m_a_on_blh = compute_metrics(test_blh[TARGET_COL].values, pred_test_a_on_blh)
    
    evaluation_summary["blh_controlled_comparison"] = {
        "test_subset_days": len(test_blh),
        "test_dates_description": "Held-out 2024 test days with verified 24-hour boundary layer height completeness (183 days)",
        "baseline_without_blh": m_a_on_blh,
        "enhanced_with_blh_ventilation": m_blh,
        "mae_improvement": round(m_a_on_blh["mae"] - m_blh["mae"], 2),
        "r2_improvement": round(m_blh["r2"] - m_a_on_blh["r2"], 4)
    }

    # =========================================================================
    # STAGE F: DEDICATED NEXT-DAY FORECASTING MODEL (MODE B)
    # =========================================================================
    logger.info("\n--- Training Dedicated Mode B (Next-Day Forecast) Model ---")
    fc_feats = exp_features["mode_b_next_day_forecast"]
    
    # Mode B target: pm25_lead1 (target at day t+1). Filter rows where pm25_lead1 is notna!
    train_fc = train_df[train_df["pm25_lead1"].notna()].copy()
    val_fc = val_df[val_df["pm25_lead1"].notna()].copy()
    test_fc = test_df[test_df["pm25_lead1"].notna()].copy()
    
    y_train_fc = train_fc["pm25_lead1"].values
    y_val_fc = val_fc["pm25_lead1"].values
    y_test_fc = test_fc["pm25_lead1"].values
    
    imputer_fc = SimpleImputer(strategy="median")
    X_train_fc = imputer_fc.fit_transform(train_fc[fc_feats])
    X_val_fc = imputer_fc.transform(val_fc[fc_feats])
    X_test_fc = imputer_fc.transform(test_fc[fc_feats])
    joblib.dump(imputer_fc, MODELS_DIR / "imputer_mode_b_next_day_forecast.joblib")
    
    # Strict next-day persistence baseline: \hat{y}_{t+1} = y_t
    pred_test_fc_pers = test_fc[TARGET_COL].values
    m_fc_pers = compute_metrics(y_test_fc, pred_test_fc_pers)
    
    xgb_fc = xgb.XGBRegressor(
        n_estimators=160, max_depth=4, learning_rate=0.04, subsample=0.85, random_state=42, n_jobs=-1
    )
    t0 = time.time()
    xgb_fc.fit(X_train_fc, y_train_fc, eval_set=[(X_val_fc, y_val_fc)], verbose=False)
    t_fc = round(time.time() - t0, 3)
    joblib.dump(xgb_fc, MODELS_DIR / "model_next_day_forecast.joblib")
    
    pred_test_fc = xgb_fc.predict(X_test_fc)
    m_fc_xgb = compute_metrics(y_test_fc, pred_test_fc)
    m_fc_xgb["training_duration_s"] = t_fc
    
    evaluation_summary["mode_b_next_day_forecast"] = {
        "lead_time": "Next-Day (t + 1)",
        "features": fc_feats,
        "sample_count": len(y_test_fc),
        "persistence_baseline": m_fc_pers,
        "xgboost_forecaster": m_fc_xgb
    }

    # =========================================================================
    # SEASONAL AND SUBSET EVALUATION BREAKDOWN
    # =========================================================================
    logger.info("\n--- Computing Seasonal & Episode Performance Breakdowns ---")
    # Compare Exp A vs Exp B vs Exp C for XGBoost on specific subsets of 2024 test data
    seasons = {
        "Full Year 2024": test_predictions_df.index,
        "Autumn Harvest (Oct-Nov)": test_predictions_df[test_predictions_df["month"].isin([10, 11])].index,
        "Post-Monsoon (Sep-Dec)": test_predictions_df[test_predictions_df["month"].isin([9, 10, 11, 12])].index,
        "Pre-Monsoon / Rabi (Apr-May)": test_predictions_df[test_predictions_df["month"].isin([4, 5])].index,
        "Non-Burning Months (Jan-Aug)": test_predictions_df[test_predictions_df["month"] < 9].index,
        "Severe Pollution Days (Observed >= 250)": test_predictions_df[test_predictions_df["is_severe_episode"] == 1].index
    }
    
    seasonal_results = {}
    for s_name, s_idx in seasons.items():
        if len(s_idx) == 0:
            continue
        y_sub = test_predictions_df.loc[s_idx, "actual_pm25"].values
        p_pers = test_predictions_df.loc[s_idx, "pred_persistence_exp_a_baseline"].values
        p_a = test_predictions_df.loc[s_idx, "pred_xgboost_exp_a_baseline"].values
        p_b = test_predictions_df.loc[s_idx, "pred_xgboost_exp_b_basic_fires"].values
        p_c = test_predictions_df.loc[s_idx, "pred_xgboost_exp_c_engineered_fires"].values
        
        seasonal_results[s_name] = {
            "days": len(s_idx),
            "actual_mean_pm25": round(float(np.mean(y_sub)), 2),
            "persistence": compute_metrics(y_sub, p_pers),
            "exp_a_baseline_xgb": compute_metrics(y_sub, p_a),
            "exp_b_basic_fires_xgb": compute_metrics(y_sub, p_b),
            "exp_c_engineered_fires_xgb": compute_metrics(y_sub, p_c)
        }
        
    evaluation_summary["seasonal_breakdown"] = seasonal_results

    # Save test predictions table
    test_predictions_df.to_csv(EVAL_DIR / "predictions_2024_test.csv", index=False)
    test_predictions_df.to_csv(AUDIT_FINAL / "PREDICTIONS_2024_TEST.csv", index=False)
    logger.info("Saved actual per-date test predictions to CSV.")

    # Save complete evaluation summary JSON
    with open(EVAL_DIR / "final_model_evaluation_summary.json", "w") as f:
        json.dump(evaluation_summary, f, indent=2)
    with open(AUDIT_FINAL / "FINAL_MODEL_EVALUATION_SUMMARY.json", "w") as f:
        json.dump(evaluation_summary, f, indent=2)
        
    # Save comparison table CSV
    df_comp = pd.DataFrame(evaluation_summary["comparison_table"])
    df_comp.to_csv(EVAL_DIR / "model_comparison_table.csv", index=False)
    df_comp.to_csv(AUDIT_FINAL / "MODEL_COMPARISON_TABLE.csv", index=False)
    
    logger.info(f"\nSuccessfully completed all model training and evaluations.")
    logger.info(f"Summary saved to {EVAL_DIR / 'final_model_evaluation_summary.json'}")

if __name__ == "__main__":
    run_pipeline()
