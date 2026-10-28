"""Master Execution Pipeline for Tracing the Smoke:
Runs Phases 3, 4, 5, 6 sequentially:
Phase 3: Data Preprocessing and Cleaning
Phase 4: Geospatial Feature Engineering & Dataset Compilation
Phase 5: Model Training with Chronological Validation (Ridge, RF, XGBoost, LightGBM, Persistence)
Phase 6: Evaluation, Severe Episode Detection, Feature Set Ablation, and SHAP Explainability
Also generates EDA figures into artifacts/figures/.
"""

import sys
import os
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from src.preprocessing.cpcb_preprocessor import CPCBPreprocessor
from src.features.feature_builder import FeatureBuilder
from src.models.train_models import ModelTrainer, FEATURE_SETS
from src.evaluation.evaluate_models import ModelEvaluator
from src.explainability.shap_explainer import SHAPExplainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_pipeline")

def generate_eda_figures(df_ml: pd.DataFrame, figures_dir: Path):
    """Generate high-resolution EDA figures saved to artifacts/figures/."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="darkgrid")
    
    # 1. PM2.5 Multi-year Trend & Severe Episode Distribution
    plt.figure(figsize=(12, 5))
    plt.plot(pd.to_datetime(df_ml["date_str"]), df_ml["delhi_daily_pm25_ugm3"], color="#06B6D4", label="Daily Mean PM2.5 (ug/m3)", linewidth=1.5)
    plt.axhline(settings.SEVERE_PM25_THRESHOLD, color="#EF4444", linestyle="--", label="NAAQS Severe Threshold (250 ug/m3)")
    plt.title("Delhi Daily Mean PM2.5 Concentration (2019 - 2024 Autumn/Winter Seasons)", fontsize=13, fontweight="bold")
    plt.xlabel("Date")
    plt.ylabel("PM2.5 (ug/m3)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_pm25_timeseries.png", dpi=200)
    plt.close()
    
    # 2. Fire Activity vs Delhi PM2.5 Scatter & Regression
    plt.figure(figsize=(8, 6))
    sns.regplot(
        data=df_ml,
        x="fire_upwind_weighted_frp_lag1",
        y="delhi_daily_pm25_ugm3",
        scatter_kws={"alpha": 0.5, "color": "#F59E0B"},
        line_kws={"color": "#EF4444", "linewidth": 2}
    )
    plt.title("Delhi PM2.5 vs Upwind Fire Activity (Lag 1 Day)", fontsize=12, fontweight="bold")
    plt.xlabel("Upwind Distance-Weighted FRP (Lag 1)")
    plt.ylabel("Delhi Daily PM2.5 (ug/m3)")
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_fire_vs_pm25.png", dpi=200)
    plt.close()
    
    # 3. Monthly PM2.5 Boxplot
    plt.figure(figsize=(8, 5))
    sns.boxplot(data=df_ml, x="month", y="delhi_daily_pm25_ugm3", hue="month", palette="Blues_d", legend=False)
    plt.title("Monthly PM2.5 Distribution (Sep - Dec)", fontsize=12, fontweight="bold")
    plt.xlabel("Month (9=Sep, 10=Oct, 11=Nov, 12=Dec)")
    plt.ylabel("PM2.5 (ug/m3)")
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_monthly_pm25_distribution.png", dpi=200)
    plt.close()

    logger.info("EDA figures successfully generated in artifacts/figures/.")

def main():
    logger.info("==================================================================")
    logger.info("  STARTING END-TO-END PIPELINE: PREPROCESSING -> ML -> EVAL -> SHAP")
    logger.info("==================================================================")
    
    # --- PHASE 3: PREPROCESSING ---
    logger.info("\n--- Phase 3: Preprocessing CPCB Station Observations ---")
    cpcb_prep = CPCBPreprocessor()
    city_out, station_out = cpcb_prep.process()
    df_city = pd.read_parquet(city_out)
    logger.info(f"Phase 3 Complete: Aggregated {len(df_city)} daily citywide PM2.5 records.")

    # --- PHASE 4: FEATURE ENGINEERING ---
    logger.info("\n--- Phase 4: Constructing Wind-Aware Geospatial Features ---")
    raw_fires_path = settings.DATA_RAW_DIR / "firms" / "punjab_haryana_fires_2019_2024.parquet"
    raw_era5_path = settings.DATA_RAW_DIR / "era5" / "era5_hourly_2019_2024.parquet"
    
    df_fires = pd.read_parquet(raw_fires_path)
    df_era5 = pd.read_parquet(raw_era5_path)
    
    builder = FeatureBuilder()
    df_ml = builder.merge_and_build_features(df_city, df_fires, df_era5)
    logger.info(f"Phase 4 Complete: ML feature dataset built with {df_ml.shape[0]} rows, {df_ml.shape[1]} columns.")
    
    # Generate EDA figures
    generate_eda_figures(df_ml, settings.FIGURES_DIR)

    # --- PHASE 5: MODEL TRAINING ---
    logger.info("\n--- Phase 5: Training ML Models with Chronological Validation ---")
    trainer = ModelTrainer()
    train_df, val_df, test_df = trainer.load_and_split()
    all_trained_models = trainer.train_all_experiments()
    logger.info("Phase 5 Complete: All models trained and serialized.")

    # --- PHASE 6: EVALUATION & ABLATION ---
    logger.info("\n--- Phase 6: Evaluating Models, Episode Identification, and Ablation ---")
    evaluator = ModelEvaluator()
    eval_results = evaluator.evaluate_all(all_trained_models, test_df)
    logger.info(f"Phase 6 Evaluation Table Summary:\n{pd.DataFrame(eval_results['comparison_table'])[['experiment', 'model', 'mae', 'rmse', 'r2', 'f1_score']]}")

    # --- PHASE 6.2: SHAP EXPLAINABILITY ---
    logger.info("\n--- Phase 6.2: Computing SHAP Global & Local Attribution ---")
    best_xgb = all_trained_models["exp_c_engineered_fires"]["xgboost"]["model"]
    feat_cols_c = FEATURE_SETS["exp_c_engineered_fires"]
    
    explainer = SHAPExplainer()
    shap_results = explainer.compute_explanations(best_xgb, feat_cols_c, test_df, model_name="xgboost")
    logger.info(f"Top 5 SHAP Features: {[f['feature'] + ': ' + str(f['importance']) for f in shap_results['global_importance'][:5]]}")

    logger.info("\n==================================================================")
    logger.info("  ALL PIPELINE PHASES (3, 4, 5, 6) EXECUTED AND VERIFIED SUCCESSFULLY")
    logger.info("==================================================================")

if __name__ == "__main__":
    main()
