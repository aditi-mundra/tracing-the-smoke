"""Model-based counterfactual scenarios for reduced Punjab-Haryana fire activity.

Reuses the already trained Exp C model and preprocessing. Only fire-dependent
inputs are scaled; every other input stays at its observed value. Results are
model-based scenarios, not proven causal effects.
"""

import numpy as np
import pandas as pd

SCENARIO_REDUCTIONS = [25, 50, 75, 100]

# Exp C fire inputs that scale in proportion to the number of fires removed.
SCALABLE_FIRE_FEATURES = ["fire_count_total", "fire_count_upwind", "fire_upwind_weighted_frp"]

DISCLAIMER = (
    "Model-based counterfactual scenario, not a proven causal effect. Fire inputs are scaled "
    "and all other inputs (including previous-day PM2.5) are held at observed values. "
    "A given percentage cut in fires does not imply the same percentage cut in PM2.5."
)


def add_pm25_lags(df: pd.DataFrame) -> pd.DataFrame:
    """Add pm25_lag1 / pm25_lag2 (same definition as scripts/build_final_ml_dataset.py) if missing."""
    df = df.copy()
    dates = pd.to_datetime(df["date_str"])
    pm25 = pd.Series(df["delhi_daily_pm25_ugm3"].values, index=dates)
    pm25[~df["cpcb_valid"].values] = np.nan
    for days in (1, 2):
        name = f"pm25_lag{days}"
        if name not in df.columns:
            df[name] = pm25.shift(days, freq="D").reindex(dates).values
    return df


def apply_fire_reduction(row: pd.Series, feature_cols: list, reduction_pct: float) -> pd.Series:
    """Return a copy of row with every fire-dependent model input reduced by reduction_pct."""
    if not 0 <= reduction_pct <= 100:
        raise ValueError(f"reduction_pct must be between 0 and 100, got {reduction_pct}")

    fire_cols = [c for c in feature_cols if "fire" in c]
    unsupported = [c for c in fire_cols if c not in SCALABLE_FIRE_FEATURES]
    if unsupported:
        raise ValueError(f"Cannot scale fire features consistently: {unsupported}")

    scenario_row = row.copy()
    for col in fire_cols:
        value = scenario_row[col]
        if pd.isna(value) or value < 0:
            raise ValueError(f"Invalid fire input {col}={value}")
        scenario_row[col] = float(value) * (1 - reduction_pct / 100)
    return scenario_row


def predict_pm25(model, imputer, scaler, feature_cols: list, row: pd.Series) -> float:
    """Predict PM2.5 for one row exactly as DataService.run_inference does."""
    X = imputer.transform(pd.DataFrame([row[feature_cols]], columns=feature_cols))
    if scaler is not None:
        X = scaler.transform(X)
    return float(model.predict(X)[0])


def compare_predictions(baseline: float, scenario: float) -> dict:
    """Absolute and percentage difference; percentage is None if the baseline is unusable."""
    difference = scenario - baseline
    baseline_is_valid = np.isfinite(baseline) and baseline > 0
    percent = difference / baseline * 100 if baseline_is_valid else None
    return {
        "baseline_pm25": baseline,
        "scenario_pm25": scenario,
        "absolute_difference": difference,
        "percent_difference": percent,
    }


def simulate_fire_reduction(model, imputer, scaler, feature_cols: list, row: pd.Series) -> dict:
    """Run the baseline and every scenario in SCENARIO_REDUCTIONS for one date's inputs."""
    baseline = predict_pm25(model, imputer, scaler, feature_cols, row)
    scenarios = []
    for reduction_pct in SCENARIO_REDUCTIONS:
        scenario_row = apply_fire_reduction(row, feature_cols, reduction_pct)
        scenario = predict_pm25(model, imputer, scaler, feature_cols, scenario_row)
        result = compare_predictions(baseline, scenario)
        scenarios.append({"fire_reduction_pct": reduction_pct, **result})
    return {"baseline_pm25": baseline, "scenarios": scenarios}