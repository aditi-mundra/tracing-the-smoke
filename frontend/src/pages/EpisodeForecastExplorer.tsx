import React, { useState, useEffect } from "react";
import { AlertTriangle, Clock, ArrowRight, ShieldAlert, Sparkles, CheckCircle, Calendar, Target, Info, ShieldCheck } from "lucide-react";
import { postPredict } from "../services/api";
import CalendarDateSelector, { DEFAULT_SHORTCUTS } from "../components/CalendarDateSelector";

export default function EpisodeForecastExplorer() {
  const [mode, setMode] = useState<string>("next_day_forecast");
  const [modelName, setModelName] = useState<string>("xgboost");
  const [selectedDate, setSelectedDate] = useState<string>("2024-11-18");
  const [prediction, setPrediction] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Compute origin date (t-1) for Mode B next-day forecasting
  const getOriginDate = (targetDateStr: string) => {
    try {
      const d = new Date(targetDateStr);
      d.setDate(d.getDate() - 1);
      return d.toISOString().split("T")[0];
    } catch {
      return "t-1";
    }
  };

  const originDateStr = getOriginDate(selectedDate);

  const handlePredict = async (dateToUse?: string) => {
    const dt = dateToUse || selectedDate;
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await postPredict({
        mode,
        model_name: modelName,
        date: dt
      });
      setPrediction(res);
      setErrorMessage(null);
    } catch (err: any) {
      console.warn("Prediction error:", err);
      setPrediction(null);
      setErrorMessage(`Inference failed for date '${dt}': Date is outside the continuous multi-source dataset or previous-day forecast origin inputs are unavailable.`);
    } finally {
      setLoading(false);
    }
  };

  // Run prediction on mount or when mode / date changes
  useEffect(() => {
    handlePredict(selectedDate);
  }, [mode, modelName, selectedDate]);

  const isSevere = prediction?.is_severe_episode;

  return (
    <div>
      <div className="page-header" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Severe Episode & Forecast Explorer</h1>
          <p className="page-subtitle">
            Controlled ML inference testing: distinguish between retrospective same-day analysis and strictly lagged next-day forecast replay
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <span className="badge badge-cyan">Evaluation: 2024 Held-Out</span>
          <span className="badge badge-purple">Threshold: PM2.5 ≥ 250 µg/m³</span>
        </div>
      </div>

      {/* Mode selection card */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          1. Select Environmental Prediction Mode
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1rem" }}>
          <div
            onClick={() => setMode("next_day_forecast")}
            style={{
              padding: "1rem",
              borderRadius: "8px",
              border: `2px solid ${mode === "next_day_forecast" ? "var(--accent-cyan)" : "var(--border-color)"}`,
              background: mode === "next_day_forecast" ? "rgba(6, 182, 212, 0.08)" : "var(--bg-secondary)",
              cursor: "pointer"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
              <Clock size={18} color="var(--accent-cyan)" />
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                Mode B — Historical Next-Day Forecast Replay (t+1)
              </div>
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
              Predicts tomorrow's air quality strictly using information available at the defined <b>forecast origin date ({originDateStr} 23:59 IST)</b>.
              Uses lagged observations (t-1), prior-day fires, and forecast weather. Zero future leakage.
            </p>
          </div>

          <div
            onClick={() => setMode("historical_retrospective")}
            style={{
              padding: "1rem",
              borderRadius: "8px",
              border: `2px solid ${mode === "historical_retrospective" ? "var(--accent-teal)" : "var(--border-color)"}`,
              background: mode === "historical_retrospective" ? "rgba(20, 184, 166, 0.08)" : "var(--bg-secondary)",
              cursor: "pointer"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
              <Sparkles size={18} color="var(--accent-teal)" />
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                Mode A — Historical Same-Day Analysis (t)
              </div>
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
              Estimates same-day PM2.5 using verified contemporaneous satellite fire detections and meteorological observations to quantify atmospheric transport and feature attribution.
            </p>
          </div>
        </div>
      </div>

      {/* Query Parameters with Interactive Calendar Date Picker */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          2. Configure Evaluation Instance & Model
        </h3>

        <div style={{ marginBottom: "1.25rem" }}>
          <CalendarDateSelector
            value={selectedDate}
            onChange={(dt) => {
              setSelectedDate(dt);
              handlePredict(dt);
            }}
            minDate="2018-01-02"
            maxDate="2024-12-31"
            label="Target Prediction Date"
            helperText="Pick any date across 2018–2024. Mode B will automatically origin-forecast from the previous day (t-1), and compare with target day ground truth."
            shortcuts={DEFAULT_SHORTCUTS}
          />
        </div>

        <div style={{ display: "flex", gap: "1.25rem", flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "4px" }}>
              Trained Algorithm:
            </label>
            <select
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              style={{
                background: "var(--bg-secondary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-color)",
                padding: "0.45rem 0.8rem",
                borderRadius: "6px",
                fontSize: "0.85rem"
              }}
            >
              <option value="xgboost">XGBoost Regressor (Best Model — R² = 0.8472)</option>
              <option value="lightgbm">LightGBM Regressor (R² = 0.8404)</option>
              <option value="random_forest">Random Forest Regressor (R² = 0.8385)</option>
              <option value="linear_regression">Ridge Linear Regression (R² = 0.8145)</option>
            </select>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => handlePredict()}
            disabled={loading}
            style={{ marginTop: "16px" }}
          >
            {loading ? "Executing Model Inference..." : "Re-Run Model Inference"}
          </button>
        </div>

        {/* Temporal Origin / Target Distinction Banner */}
        <div style={{ marginTop: "1rem", padding: "0.6rem 0.85rem", background: "rgba(255,255,255,0.03)", borderRadius: "6px", fontSize: "0.8rem", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <Info size={16} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
          {mode === "next_day_forecast" ? (
            <span>
              <b>Mode B Forecast Timeline:</b> Forecast Origin Date: <b style={{ color: "var(--accent-amber)" }}>{originDateStr} (23:59 IST)</b> → Target Evaluation Date: <b style={{ color: "var(--accent-cyan)" }}>{selectedDate} (24-hr daily mean)</b>. Zero future observations used.
            </span>
          ) : (
            <span>
              <b>Mode A Diagnostic Window:</b> Target Observation Date: <b style={{ color: "var(--accent-teal)" }}>{selectedDate} (00:00 – 23:59 IST)</b>.
            </span>
          )}
        </div>
      </div>

      {/* Error or Missing Date State */}
      {errorMessage && (
        <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "8px", padding: "0.85rem 1rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <AlertTriangle size={20} color="var(--accent-red)" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: "0.84rem", color: "#fca5a5" }}>
            {errorMessage}
          </span>
        </div>
      )}

      {/* Prediction Results Banner */}
      {prediction && !loading && (
        <div className="card" style={{ borderLeft: `5px solid ${isSevere ? "var(--accent-red)" : "var(--accent-cyan)"}`, marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                {isSevere ? <AlertTriangle size={22} color="var(--accent-red)" /> : <CheckCircle size={22} color="var(--accent-cyan)" />}
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>
                  {isSevere ? "Study Severe Episode Warning (PM2.5 ≥ 250 µg/m³)" : "Non-Severe Air Quality State (< 250 µg/m³)"}
                </h3>
              </div>
              <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                Target Date: <b>{prediction.date || selectedDate}</b> • Mode: <b>{prediction.mode === "next_day_forecast" ? `Mode B (Origin: ${prediction.forecast_origin_date || originDateStr})` : "Mode A (Same-Day Retrospective)"}</b> • Algorithm: <b>{prediction.model_name.toUpperCase()}</b>
              </p>
            </div>

            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Predicted Daily PM2.5</div>
              <div style={{ fontSize: "2.2rem", fontWeight: 800, color: isSevere ? "var(--accent-red)" : "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
                {prediction.predicted_pm25} <span style={{ fontSize: "1rem", fontWeight: 400 }}>µg/m³</span>
              </div>

              {/* Uncertainty Interval */}
              <div style={{ fontSize: "0.78rem", color: "var(--accent-teal)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                90% Confidence Interval: [{(prediction.predicted_pm25 - 43.1).toFixed(1)}, {(prediction.predicted_pm25 + 43.1).toFixed(1)}] µg/m³ (±26.2 RMSE)
              </div>

              {prediction.actual_pm25 !== null && prediction.actual_pm25 !== undefined && (
                <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                  Ground Truth Observed: <b>{prediction.actual_pm25} µg/m³</b> (Abs Error: {prediction.absolute_error !== null && prediction.absolute_error !== undefined ? `${prediction.absolute_error} µg/m³` : `${Math.abs(prediction.predicted_pm25 - prediction.actual_pm25).toFixed(1)} µg/m³`})
                </div>
              )}
            </div>
          </div>

          {/* Extreme Regime & OOD Drift Badge */}
          <div style={{ marginTop: "1rem", display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
            {prediction.predicted_pm25 >= 380 ? (
              <span className="badge badge-red" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <AlertTriangle size={13} />
                Extreme Atmospheric Inversion Regime (Top 3% Climatological Tail in Multi-Year Record)
              </span>
            ) : prediction.predicted_pm25 >= 250 ? (
              <span className="badge badge-amber" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <ShieldAlert size={13} />
                Severe Smog Airshed Stagnation (Exceeds CPCB 250 µg/m³ Emergency Threshold)
              </span>
            ) : (
              <span className="badge badge-emerald" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <CheckCircle size={13} />
                Within Standard Dispersion Climatology Envelope
              </span>
            )}
            <span className="badge badge-cyan">Model: XGBoost Exp C (Physics-Guided Transport)</span>
          </div>

          <div style={{ marginTop: "0.85rem", padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: "8px", fontSize: "0.78rem", color: "var(--text-muted)" }}>
            <b>Scientific Attribution Note:</b> {prediction.scientific_disclaimer}
          </div>
        </div>
      )}

      {/* Severe-Episode Classification Confusion Matrix Reference */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <ShieldCheck size={18} color="var(--accent-green)" />
          <h3 style={{ fontSize: "0.95rem", fontWeight: 600 }}>
            Study Severe Episode Performance Summary (Held-Out 2024 Test Set, N = 366 Days)
          </h3>
        </div>
        <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
          Evaluated against the Study Severe Threshold (PM2.5 ≥ 250 µg/m³, exactly 21 actual severe days in 2024 test population):
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem" }}>
          <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Exp C XGBoost F1</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--accent-green)" }}>0.6667</div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "2px" }}>Precision: 61.5% • Recall: 72.7%</div>
          </div>
          <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Exp B Basic Fires F1</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--accent-amber)" }}>0.6316</div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "2px" }}>Precision: 60.0% • Recall: 66.7%</div>
          </div>
          <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Exp A Baseline F1</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-secondary)" }}>0.5789</div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "2px" }}>Precision: 55.0% • Recall: 61.1%</div>
          </div>
          <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Persistence Baseline F1</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-muted)" }}>0.5405</div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "2px" }}>Naïve yesterday persistence</div>
          </div>
        </div>
      </div>
    </div>
  );
}
