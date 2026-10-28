"""SHAP Explainability and Model Attribution Module.
Computes:
1. Global TreeSHAP feature importances (mean absolute SHAP values).
2. Grouped attribution across 4 primary physical categories:
   - Fire Activity and Atmospheric Transport
   - Meteorological & Inversion Conditions
   - Historical Pollution Persistence
   - Seasonal and Calendar Effects
3. Local date-level SHAP explanations (waterfall breakdown of feature pushes).
4. Severe-episode specific feature attribution.
5. Scientific limitation and non-causal disclaimer embedding.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import shap

from backend.app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("shap_explainer")

# Defined feature groups for grouped attribution
FEATURE_GROUPS = {
    "Fire Activity & Transport": [
        "fire_count_total", "fire_count_punjab", "fire_count_haryana",
        "fire_count_upwind", "fire_upwind_weighted_frp", "fire_distance_weighted_count",
        "fire_distance_mean_km", "fire_count_near_150km", "fire_count_mid_150_300km",
        "fire_upwind_weighted_frp_lag1", "fire_upwind_weighted_frp_lag2", "fire_upwind_rolling_3d",
        "fire_frp_total", "fire_frp_mean"
    ],
    "Meteorology & Inversion": [
        "temp_mean", "temp_min", "rh_mean", "dew_point_mean", "surface_pressure_mean",
        "wind_speed_mean", "wind_speed_max", "u_wind_mean", "v_wind_mean",
        "blh_mean", "blh_min", "ventilation_index"
    ],
    "Historical Pollution": [
        "pm25_lag1", "pm25_lag2", "pm25_rolling_3d", "pm25_rolling_7d"
    ],
    "Seasonal & Calendar": [
        "month", "doy_sin", "doy_cos", "is_weekend"
    ]
}

SCIENTIFIC_DISCLAIMER = (
    "Scientific Qualification: SHAP measures the statistical attribution and predictive influence of features "
    "within the trained machine learning model. It reflects how heavily the algorithm relies on specific variables "
    "to form its prediction. It does not represent exact physical source-apportionment percentages or direct causal "
    "fractions of Delhi's particulate matter originating from agricultural fires."
)

class SHAPExplainer:
    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.shap_dir = (artifacts_dir or settings.SHAP_DIR)
        self.shap_dir.mkdir(parents=True, exist_ok=True)
        
    def compute_explanations(
        self,
        model: Any,
        feature_cols: List[str],
        test_df: pd.DataFrame,
        model_name: str = "xgboost"
    ) -> Dict[str, Any]:
        """Compute TreeSHAP explanations for test dataset observations."""
        logger.info(f"Computing SHAP explanations for {model_name} on {len(test_df)} test observations...")
        
        X_test = test_df[feature_cols].copy()
        dates = test_df["date_str"].tolist()
        actual_pm25 = test_df["delhi_daily_pm25_ugm3"].tolist()
        
        # Load imputer if available
        import joblib
        imputer_path = settings.TRAINED_MODELS_DIR / "imputer_exp_c_engineered_fires.joblib"
        if imputer_path.exists():
            imputer = joblib.load(imputer_path)
            X_test_imputed = pd.DataFrame(imputer.transform(X_test), columns=feature_cols)
        else:
            X_test_imputed = X_test.fillna(X_test.median())
        
        # Initialize TreeExplainer
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test_imputed)
        base_value = float(explainer.expected_value) if hasattr(explainer, "expected_value") else float(np.mean(actual_pm25))
        
        # 1. Global Mean Absolute SHAP values
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        global_importance = []
        for feat, val in zip(feature_cols, mean_abs_shap):
            # Map feature to its category
            group_name = "Other"
            for gname, gcols in FEATURE_GROUPS.items():
                if feat in gcols:
                    group_name = gname
                    break
            global_importance.append({
                "feature": feat,
                "importance": round(float(val), 3),
                "group": group_name
            })
            
        global_importance.sort(key=lambda x: x["importance"], reverse=True)
        
        # 2. Grouped Importance
        grouped_totals = {g: 0.0 for g in FEATURE_GROUPS}
        grouped_totals["Other"] = 0.0
        
        for item in global_importance:
            grouped_totals[item["group"]] += item["importance"]
            
        total_imp = sum(grouped_totals.values()) or 1.0
        grouped_summary = [
            {
                "group": g,
                "total_mean_abs_shap": round(val, 3),
                "percentage_influence": round((val / total_imp) * 100.0, 1)
            }
            for g, val in grouped_totals.items() if val > 0
        ]
        grouped_summary.sort(key=lambda x: x["total_mean_abs_shap"], reverse=True)
        
        # 3. Local explanations per date (waterfall records)
        local_explanations = {}
        for idx, dt in enumerate(dates):
            date_shap = shap_values[idx]
            feature_contributions = []
            
            for feat, s_val in zip(feature_cols, date_shap):
                group_name = "Other"
                for gname, gcols in FEATURE_GROUPS.items():
                    if feat in gcols:
                        group_name = gname
                        break
                        
                feature_contributions.append({
                    "feature": feat,
                    "value": round(float(X_test.iloc[idx][feat]), 2),
                    "shap_value": round(float(s_val), 2),
                    "group": group_name
                })
                
            # Sort by absolute SHAP impact
            feature_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            
            pred_val = base_value + float(np.sum(date_shap))
            local_explanations[dt] = {
                "date": dt,
                "actual_pm25": round(float(actual_pm25[idx]), 2),
                "predicted_pm25": round(float(pred_val), 2),
                "base_value": round(base_value, 2),
                "top_features": feature_contributions[:10],
                "all_features": feature_contributions
            }
            
        # 4. Severe episode specific SHAP attribution
        severe_indices = [i for i, y in enumerate(actual_pm25) if y >= settings.SEVERE_PM25_THRESHOLD]
        severe_importance = []
        if severe_indices:
            severe_mean_abs = np.mean(np.abs(shap_values[severe_indices]), axis=0)
            for feat, val in zip(feature_cols, severe_mean_abs):
                severe_importance.append({
                    "feature": feat,
                    "severe_importance": round(float(val), 3)
                })
            severe_importance.sort(key=lambda x: x["severe_importance"], reverse=True)
            
        output = {
            "model_name": model_name,
            "base_value": round(base_value, 2),
            "disclaimer": SCIENTIFIC_DISCLAIMER,
            "global_importance": global_importance,
            "grouped_importance": grouped_summary,
            "severe_importance": severe_importance,
            "local_explanations": local_explanations
        }
        
        out_file = self.shap_dir / f"shap_explanations_{model_name}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            
        logger.info(f"Saved SHAP explanations to {out_file}")
        return output

if __name__ == "__main__":
    pass
