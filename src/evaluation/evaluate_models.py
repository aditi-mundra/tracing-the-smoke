"""Model Evaluation and Experimental Comparative Analysis Module.
Calculates:
1. PM2.5 Regression Metrics: MAE, RMSE, R2 on held-out test set.
2. Severe Pollution Episode Identification:
   - Threshold: >= 250 ug/m3 (NAAQS Severe Category).
   - Metrics: Precision, Recall, F1-Score, Confusion Matrix.
3. Feature Set Ablation Comparison (Research Questions RQ2 and RQ3):
   - Exp A (Baseline) vs Exp B (Basic Fires) vs Exp C (Wind-Aware Engineered Fires).
   - Answers whether fire information and transport heuristics improve out-of-sample prediction.
4. Generates evaluation artifacts and comparative tables.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, confusion_matrix, precision_recall_fscore_support

from backend.app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_models")

class ModelEvaluator:
    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.eval_dir = (artifacts_dir or settings.EVALUATION_DIR)
        self.eval_dir.mkdir(parents=True, exist_ok=True)
        
    @staticmethod
    def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Compute standard regression metrics."""
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))
        return {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 4)
        }

    @staticmethod
    def compute_severe_episode_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        threshold: float = settings.SEVERE_PM25_THRESHOLD
    ) -> Dict[str, Any]:
        """Evaluate identification of severe pollution episodes (PM2.5 >= threshold)."""
        true_binary = (y_true >= threshold).astype(int)
        pred_binary = (y_pred >= threshold).astype(int)
        
        cm = confusion_matrix(true_binary, pred_binary, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            true_binary, pred_binary, average="binary", zero_division=0
        )
        
        return {
            "threshold_ugm3": threshold,
            "actual_severe_episodes": int(true_binary.sum()),
            "predicted_severe_episodes": int(pred_binary.sum()),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_negatives": int(tn),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "confusion_matrix": {
                "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)
            }
        }

    def evaluate_all(
        self,
        trained_results: Dict[str, Dict[str, Any]],
        test_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Evaluate all models across all experiments on the held-out test dataset."""
        logger.info("Evaluating models and generating comparative tables...")
        y_test = test_df[settings.DELHI_LATITUDE if False else "delhi_daily_pm25_ugm3"].values
        test_dates = test_df["date_str"].tolist()
        
        evaluation_report = {
            "test_period": "2024 held-out out-of-time test set",
            "test_sample_size": len(y_test),
            "experiments": {},
            "comparison_table": [],
            "ablation_summary": {},
            "predictions_by_date": {}
        }
        
        # Populate predictions by date for UI time-series inspection
        for dt, actual in zip(test_dates, y_test):
            evaluation_report["predictions_by_date"][dt] = {
                "actual_pm25": round(float(actual), 2),
                "models": {}
            }
            
        for exp_name, exp_models in trained_results.items():
            exp_metrics = {}
            for model_name, model_info in exp_models.items():
                y_pred_test = model_info["test_pred"]
                reg_metrics = self.compute_regression_metrics(y_test, y_pred_test)
                episode_metrics = self.compute_severe_episode_metrics(y_test, y_pred_test)
                
                # Record predictions per date
                for dt, pred in zip(test_dates, y_pred_test):
                    evaluation_report["predictions_by_date"][dt]["models"][f"{model_name}_{exp_name}"] = round(float(pred), 2)
                    
                entry = {
                    "experiment": exp_name,
                    "model": model_name,
                    "mae": reg_metrics["mae"],
                    "rmse": reg_metrics["rmse"],
                    "r2": reg_metrics["r2"],
                    "precision": episode_metrics["precision"],
                    "recall": episode_metrics["recall"],
                    "f1_score": episode_metrics["f1_score"],
                    "confusion_matrix": episode_metrics["confusion_matrix"]
                }
                exp_metrics[model_name] = entry
                evaluation_report["comparison_table"].append(entry)
                
            evaluation_report["experiments"][exp_name] = exp_metrics
            
        # Compute Ablation: compare best model (e.g. XGBoost / LightGBM) across Exp A, Exp B, Exp C
        ref_model = "xgboost"
        if ref_model in evaluation_report["experiments"].get("exp_a_baseline", {}):
            base = evaluation_report["experiments"]["exp_a_baseline"][ref_model]
            exp_b = evaluation_report["experiments"].get("exp_b_basic_fires", {}).get(ref_model, base)
            exp_c = evaluation_report["experiments"].get("exp_c_engineered_fires", {}).get(ref_model, base)
            
            evaluation_report["ablation_summary"] = {
                "evaluated_algorithm": ref_model,
                "exp_a_mae": base["mae"],
                "exp_b_mae": exp_b["mae"],
                "exp_c_mae": exp_c["mae"],
                "improvement_basic_fires_mae": round(base["mae"] - exp_b["mae"], 2),
                "improvement_engineered_fires_mae": round(base["mae"] - exp_c["mae"], 2),
                "exp_a_r2": base["r2"],
                "exp_b_r2": exp_b["r2"],
                "exp_c_r2": exp_c["r2"],
                "improvement_r2_over_baseline": round(exp_c["r2"] - base["r2"], 4)
            }
            
        # Save evaluation artifacts
        eval_path = self.eval_dir / "model_evaluation_results.json"
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_report, f, indent=2)
            
        # Also save comparison table as CSV
        df_comp = pd.DataFrame(evaluation_report["comparison_table"])
        df_comp.to_csv(self.eval_dir / "model_comparison_table.csv", index=False)
        
        logger.info(f"Evaluation report successfully saved to {eval_path}")
        return evaluation_report

if __name__ == "__main__":
    pass
