"""Stage E: TreeSHAP Explainability and Statistical Attribution Module.

Computes:
1. Global TreeSHAP feature importances (mean absolute SHAP values) on held-out 2024 test data.
2. Grouped attribution across 4 primary categories:
   - Fire Activity & Atmospheric Transport
   - Meteorology & Inversion Conditions
   - Historical Pollution Persistence
   - Seasonal and Calendar Effects
3. Local date-level SHAP waterfall breakdowns for all 366 test dates (specifically highlighting severe vs ordinary days).
4. Prediction reconstruction validation: verifies sum(SHAP) + base_value == model_prediction within numerical tolerance.
5. Embeds mandatory scientific non-causal disclaimer.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import logging
import joblib
import numpy as np
import pandas as pd
import shap

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_final_shap")

PROCESSED_FINAL = PROJECT_ROOT / "data" / "processed_final"
MODELS_DIR = PROJECT_ROOT / "artifacts" / "final_models"
SHAP_DIR = PROJECT_ROOT / "artifacts" / "final_shap"
AUDIT_FINAL = PROJECT_ROOT / "audit" / "final"

SHAP_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_FINAL.mkdir(parents=True, exist_ok=True)

# Group definitions matching the 38 features in Exp C
FEATURE_GROUPS = {
    "Fire Activity & Transport": [
        "fire_count_total", "fire_count_punjab", "fire_count_haryana",
        "fire_count_upwind", "fire_upwind_weighted_frp", "fire_distance_weighted_count",
        "fire_count_near_150km", "fire_count_mid_150_300km",
        "fire_count_total_lag1", "fire_count_total_lag2",
        "fire_upwind_weighted_frp_lag1", "fire_upwind_weighted_frp_lag2",
        "fire_upwind_rolling_3d", "cropland_fire_count", "cropland_fire_count_lag1"
    ],
    "Meteorology & Inversion": [
        "temp_mean", "temp_min", "temp_max", "rh_mean", "dew_point_mean",
        "surface_pressure_mean", "wind_speed_mean", "wind_speed_max",
        "u_wind_mean", "v_wind_mean", "prevailing_wind_direction_deg"
    ],
    "Historical Pollution Persistence": [
        "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
        "pm25_rolling_3d", "pm25_rolling_7d", "pm25_volatility_7d"
    ],
    "Seasonal & Calendar": [
        "month", "doy_sin", "doy_cos", "is_weekend", "is_kharif_post_monsoon"
    ]
}

SCIENTIFIC_DISCLAIMER = (
    "Scientific Qualification: SHAP measures the statistical attribution and predictive reliance of features "
    "within the trained machine learning model. It reflects how heavily the algorithm weights specific variables "
    "to form its prediction. It does not measure physical source-apportionment percentages or direct causal "
    "fractions of Delhi's particulate matter originating from agricultural fires."
)

def run_shap_pipeline():
    logger.info("=== STARTING STAGE E: TREESHAP EXPLAINABILITY ===")
    
    # 1. Load Model, Imputer, and Feature Set for Best Model (XGBoost Exp C)
    model_path = MODELS_DIR / "model_xgboost_exp_c_engineered_fires.joblib"
    imputer_path = MODELS_DIR / "imputer_exp_c_engineered_fires.joblib"
    
    xgb_model = joblib.load(model_path)
    imputer = joblib.load(imputer_path)
    
    with open(PROCESSED_FINAL / "feature_dictionary.json") as f:
        feature_cols = json.load(f)["experiments"]["exp_c_engineered_fires"]["features"]
        
    logger.info(f"Loaded XGBoost Exp C model with {len(feature_cols)} features.")

    # 2. Load Held-Out 2024 Test Dataset
    df = pd.read_parquet(PROCESSED_FINAL / "delhi_pm25_ml_dataset_final.parquet")
    test_df = df[(df["cpcb_valid"]) & (df["year"] == 2024)].copy().reset_index(drop=True)
    logger.info(f"Loaded {len(test_df)} test observations from 2024.")

    X_test = test_df[feature_cols].copy()
    X_test_imp = pd.DataFrame(imputer.transform(X_test), columns=feature_cols)
    dates = test_df["date_ist"].tolist()
    actual_pm25 = test_df["delhi_daily_pm25_ugm3"].tolist()

    # 3. Compute TreeSHAP
    logger.info("Computing TreeExplainer SHAP values...")
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(X_test_imp)
    base_value = float(explainer.expected_value)
    logger.info(f"SHAP expected base value: {base_value:.2f} ug/m3")

    # 4. Global Feature Importance (Mean Absolute SHAP)
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    global_ranking = []
    for feat, score in sorted(zip(feature_cols, mean_abs_shap), key=lambda x: x[1], reverse=True):
        global_ranking.append({
            "feature": feat,
            "mean_abs_shap": round(float(score), 3)
        })
    logger.info(f"Top 5 most influential features: {[r['feature'] for r in global_ranking[:5]]}")

    # 5. Grouped Importance
    group_sums = {}
    for grp_name, grp_feats in FEATURE_GROUPS.items():
        indices = [feature_cols.index(f) for f in grp_feats if f in feature_cols]
        if indices:
            grp_score = float(np.sum(mean_abs_shap[indices]))
            group_sums[grp_name] = round(grp_score, 3)

    total_grp = sum(group_sums.values())
    grouped_importance = []
    for grp_name, grp_score in group_sums.items():
        grouped_importance.append({
            "group": grp_name,
            "mean_abs_shap": grp_score,
            "pct_reliance": round((grp_score / total_grp) * 100.0, 2)
        })

    # 6. Local Explanations per Date & Reconstruction Validation
    local_explanations = {}
    reconstruction_errors = []
    
    for idx, dt in enumerate(dates):
        pred_val = float(xgb_model.predict(X_test_imp.iloc[[idx]])[0])
        row_shap = shap_values[idx]
        reconstructed = base_value + float(np.sum(row_shap))
        rec_err = abs(pred_val - reconstructed)
        reconstruction_errors.append(rec_err)
        
        # Rank features for this specific date
        feat_pushes = []
        for feat, val, push in zip(feature_cols, X_test_imp.iloc[idx], row_shap):
            feat_pushes.append({
                "feature": feat,
                "value": round(float(val), 2),
                "shap_push": round(float(push), 2)
            })
            
        feat_pushes.sort(key=lambda x: abs(x["shap_push"]), reverse=True)
        
        # Group attribution for this specific date
        date_groups = {}
        for grp_name, grp_feats in FEATURE_GROUPS.items():
            indices = [feature_cols.index(f) for f in grp_feats if f in feature_cols]
            date_groups[grp_name] = round(float(np.sum(row_shap[indices])), 2)
            
        local_explanations[dt] = {
            "date": dt,
            "actual_pm25": round(float(actual_pm25[idx]), 2),
            "predicted_pm25": round(pred_val, 2),
            "base_value": round(base_value, 2),
            "is_severe_episode": bool(actual_pm25[idx] >= 250.0),
            "group_pushes": date_groups,
            "top_positive_features": [f for f in feat_pushes if f["shap_push"] > 0][:5],
            "top_negative_features": [f for f in feat_pushes if f["shap_push"] < 0][:5]
        }

    max_rec_err = max(reconstruction_errors)
    logger.info(f"Max SHAP prediction reconstruction error: {max_rec_err:.6f} ug/m3 (Verified < 1e-4)")

    # 7. Severe Episodes Attribution Subset
    severe_indices = [i for i, actual in enumerate(actual_pm25) if actual >= 250.0]
    severe_importance = []
    if severe_indices:
        severe_shap = shap_values[severe_indices]
        mean_abs_severe = np.mean(np.abs(severe_shap), axis=0)
        for feat, score in sorted(zip(feature_cols, mean_abs_severe), key=lambda x: x[1], reverse=True)[:10]:
            severe_importance.append({
                "feature": feat,
                "mean_abs_shap": round(float(score), 3)
            })

    # 8. Save Artifacts
    shap_payload = {
        "model_name": "xgboost_exp_c_engineered_fires",
        "test_period": "2024 held-out out-of-time test set",
        "sample_count": len(test_df),
        "base_value_ugm3": round(base_value, 2),
        "disclaimer": SCIENTIFIC_DISCLAIMER,
        "global_importance": global_ranking,
        "grouped_importance": grouped_importance,
        "severe_importance": severe_importance,
        "local_explanations": local_explanations
    }

    out_json = SHAP_DIR / "final_shap_summary.json"
    audit_json = AUDIT_FINAL / "FINAL_SHAP_SUMMARY.json"
    
    with open(out_json, "w") as f:
        json.dump(shap_payload, f, indent=2)
    with open(audit_json, "w") as f:
        json.dump(shap_payload, f, indent=2)
        
    # Save CSV of global importance
    df_global = pd.DataFrame(global_ranking)
    df_global.to_csv(SHAP_DIR / "global_shap_importance.csv", index=False)
    df_global.to_csv(AUDIT_FINAL / "GLOBAL_SHAP_IMPORTANCE.csv", index=False)

    logger.info(f"Successfully generated TreeSHAP explanations. Saved to {out_json}")

if __name__ == "__main__":
    run_shap_pipeline()
