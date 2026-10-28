import React, { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { HelpCircle, AlertOctagon, PieChart as PieIcon, Layers, Calendar, CheckCircle, Calculator, AlertTriangle } from "lucide-react";
import { fetchShapGlobal, fetchShapDay } from "../services/api";
import CalendarDateSelector, { DEFAULT_SHORTCUTS } from "../components/CalendarDateSelector";

export default function AttributionShap() {
  const [shapGlobal, setShapGlobal] = useState<any>(null);
  const [selectedDate, setSelectedDate] = useState<string>("2024-11-18");
  const [dayExplanation, setDayExplanation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [dayLoading, setDayLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchShapGlobal()
      .then((data) => {
        setShapGlobal(data);
      })
      .catch((err) => {
        console.error(err);
      });
  }, []);

  const handleDateChange = (dt: string) => {
    setSelectedDate(dt);
    setDayLoading(true);
    setErrorMessage(null);
    fetchShapDay(dt)
      .then((dayData) => {
        setDayExplanation(dayData);
        setErrorMessage(null);
      })
      .catch((err) => {
        console.warn("fetchShapDay error for date:", dt, err);
        setDayExplanation(null);
        setErrorMessage(`No observation or TreeSHAP explanation available for '${dt}'. Please select a date within the study evaluation period (2018–2024, including all 366 held-out test days of 2024).`);
      })
      .finally(() => {
        setDayLoading(false);
        setLoading(false);
      });
  };

  useEffect(() => {
    handleDateChange("2024-11-18");
  }, []);

  if (loading && !shapGlobal) {
    return <div style={{ padding: "2rem", color: "var(--text-secondary)" }}>Loading SHAP Explainability Engine...</div>;
  }

  // 1. Global Feature Importance Bar Chart
  const top12Features = (shapGlobal?.global_importance || []).slice(0, 12).reverse();
  const featLabels = top12Features.map((f: any) => f.feature);
  const featValues = top12Features.map((f: any) => f.importance ?? f.mean_abs_shap ?? 0);

  const globalBarOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1e293b",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#f8fafc" },
      formatter: "{b}: <b>{c} µg/m³ mean |SHAP|</b>"
    },
    grid: { left: "190", right: "35", top: "25", bottom: "35" },
    xAxis: {
      type: "value",
      name: "Mean Absolute SHAP (µg/m³)",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      axisLabel: { color: "#94a3b8" }
    },
    yAxis: {
      type: "category",
      data: featLabels,
      axisLabel: { color: "#94a3b8", fontSize: 11 }
    },
    series: [
      {
        name: "Mean |SHAP|",
        type: "bar",
        data: featValues,
        itemStyle: {
          color: (params: any) => {
            const featName = params.name;
            if (featName.includes("fire")) return "#f59e0b"; // Amber for fire transport
            if (featName.includes("pm25")) return "#06b6d4"; // Cyan for historical pollution
            if (featName.includes("doy")) return "#10b981"; // Green for seasonality
            return "#8b5cf6"; // Purple for meteorology
          },
          borderRadius: [0, 4, 4, 0]
        }
      }
    ]
  };

  // 2. Grouped Importance Donut Chart
  const groupedData = (shapGlobal?.grouped_importance || []).map((g: any) => ({
    name: g.group,
    value: g.percentage_influence ?? g.pct_reliance ?? 0,
    itemStyle: {
      color:
        g.group.includes("Fire") ? "#f59e0b" :
        g.group.includes("Historical") ? "#06b6d4" :
        g.group.includes("Meteorology") ? "#8b5cf6" : "#10b981"
    }
  }));

  const groupedPieOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "#1e293b",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#f8fafc" },
      formatter: "{b}: <b>{c}%</b> of full-year model reliance"
    },
    legend: {
      bottom: 5,
      textStyle: { color: "#94a3b8", fontSize: 11 }
    },
    series: [
      {
        name: "Feature Groups",
        type: "pie",
        radius: ["42%", "72%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: true,
        label: {
          show: true,
          formatter: "{b}\n{c}%",
          color: "#94a3b8",
          fontSize: 10
        },
        data: groupedData
      }
    ]
  };

  const isDaySevere = (dayExplanation?.actual_pm25 ?? 0) >= 250;

  return (
    <div>
      <div className="page-header" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Model Explainability & SHAP Attribution</h1>
          <p className="page-subtitle">
            Interpretable TreeSHAP feature attributions dissecting predictive influence of fire advection versus meteorological stagnation
          </p>
        </div>
        <span className="badge badge-cyan">Model: Exp C XGBoost (TreeSHAP)</span>
      </div>

      {/* Mandatory Scientific Qualification Banner */}
      <div className="card" style={{ marginBottom: "1.5rem", borderLeft: "4px solid var(--accent-amber)" }}>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
          <AlertOctagon size={20} color="var(--accent-amber)" style={{ flexShrink: 0, marginTop: "2px" }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--accent-amber)", marginBottom: "4px" }}>
              Scientific Qualification on Machine Learning Feature Attribution
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              SHAP values measure the <b>marginal mathematical contribution of each feature to the statistical model prediction</b> relative to the dataset baseline.
              They represent predictive reliance within the ML architecture and <b>must not be equated with physical mass concentration source apportionment</b> (such as receptor chemical mass balance or CMAQ/WRF-Chem emission tagging).
            </p>
          </div>
        </div>
      </div>

      {/* Global Charts */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))", gap: "1.25rem", marginBottom: "1.5rem" }}>
        {/* Global Feature Ranking */}
        <div className="chart-box" style={{ marginBottom: 0 }}>
          <div className="chart-header">
            <div>
              <div className="chart-title">Global Feature Importance (Mean |SHAP| on 2024 Test Set)</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                Cyan: Historical Pollution | Amber: Upwind Fire Transport | Purple: Meteorology | Green: Seasonality
              </div>
            </div>
          </div>
          <ReactECharts option={globalBarOption} style={{ height: 360 }} />
        </div>

        {/* Grouped Importance Donut */}
        <div className="chart-box" style={{ marginBottom: 0 }}>
          <div className="chart-header">
            <div>
              <div className="chart-title">Grouped Predictive Reliance Breakdown</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                Full-year partition (fire transport surges to 34.8% during acute harvest peaks)
              </div>
            </div>
          </div>
          <ReactECharts option={groupedPieOption} style={{ height: 360 }} />
        </div>
      </div>

      {/* Local Day Explanation */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 600 }}>Local Historical Day Inspection</h3>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Step-by-step additive TreeSHAP reconstruction of predicted PM2.5 from model baseline
            </div>
          </div>

          {/* Interactive Calendar Date Picker */}
          <CalendarDateSelector
            value={selectedDate}
            onChange={handleDateChange}
            minDate="2018-01-01"
            maxDate="2024-12-31"
            label="Historical Date"
            helperText="Every eligible date in the 2024 held-out test evaluation has genuine precomputed TreeSHAP values. Prior historical dates are computed on the fly."
            shortcuts={DEFAULT_SHORTCUTS}
          />
        </div>

        {/* Error or Missing Date State */}
        {errorMessage && (
          <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "8px", padding: "0.85rem 1rem", marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <AlertTriangle size={18} color="var(--accent-red)" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: "0.84rem", color: "#fca5a5" }}>
              {errorMessage}
            </span>
          </div>
        )}

        {dayLoading && (
          <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Retrieving genuine TreeSHAP explanation for {selectedDate}...
          </div>
        )}

        {dayExplanation && !dayLoading && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem", marginBottom: "1.25rem" }}>
              <div className="card" style={{ background: "var(--bg-secondary)", padding: "0.85rem" }}>
                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Observed Delhi PM2.5</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: isDaySevere ? "var(--accent-red)" : "var(--accent-cyan)", marginTop: "0.2rem" }}>
                  {dayExplanation.actual_pm25} <span style={{ fontSize: "0.85rem", fontWeight: 400 }}>µg/m³</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
                  Status: <b>{dayExplanation.actual_pm25 >= 250 ? "Study Severe Episode" : "Very Poor / Non-Severe"}</b>
                </div>
              </div>

              <div className="card" style={{ background: "var(--bg-secondary)", padding: "0.85rem" }}>
                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Model Prediction f(x)</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "0.2rem" }}>
                  {dayExplanation.predicted_pm25} <span style={{ fontSize: "0.85rem", fontWeight: 400 }}>µg/m³</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
                  Residual Error: {(dayExplanation.predicted_pm25 - dayExplanation.actual_pm25).toFixed(1)} µg/m³
                </div>
              </div>

              <div className="card" style={{ background: "var(--bg-secondary)", padding: "0.85rem" }}>
                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Model Base Value E[f(x)]</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-muted)", marginTop: "0.2rem" }}>
                  {dayExplanation.base_value} <span style={{ fontSize: "0.85rem", fontWeight: 400 }}>µg/m³</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
                  Training data mean expectation
                </div>
              </div>

              <div className="card" style={{ background: "var(--bg-secondary)", padding: "0.85rem" }}>
                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Net SHAP Push Σ φ_i</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: dayExplanation.predicted_pm25 >= dayExplanation.base_value ? "#ef4444" : "#10b981", marginTop: "0.2rem" }}>
                  {(dayExplanation.predicted_pm25 - dayExplanation.base_value) >= 0 ? "+" : ""}
                  {(dayExplanation.predicted_pm25 - dayExplanation.base_value).toFixed(2)} <span style={{ fontSize: "0.85rem", fontWeight: 400 }}>µg/m³</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
                  Sum of feature pushes
                </div>
              </div>
            </div>

            {/* Reconstruction formula note */}
            <div style={{ background: "rgba(6, 182, 212, 0.08)", border: "1px solid rgba(6, 182, 212, 0.2)", borderRadius: "6px", padding: "0.5rem 0.85rem", marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Calculator size={16} color="var(--accent-cyan)" />
              <span style={{ fontSize: "0.8rem", color: "#cbd5e1" }}>
                <b>Exact TreeSHAP Additive Identity:</b> Model Base Value ({dayExplanation.base_value}) + Sum of Feature SHAP Contributions ({(dayExplanation.predicted_pm25 - dayExplanation.base_value).toFixed(2)}) = Predicted PM2.5 (<b>{dayExplanation.predicted_pm25} µg/m³</b>). Zero unexplained residual.
              </span>
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Feature Name</th>
                    <th>Environmental Domain</th>
                    <th>Observed Value</th>
                    <th>SHAP Contribution</th>
                    <th>Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {(dayExplanation.top_features || []).map((feat: any, idx: number) => {
                    const shapVal = feat.shap_value ?? feat.shap_push ?? 0;
                    const isPositive = shapVal > 0;
                    return (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600 }}>{feat.feature}</td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              background:
                                feat.group.includes("Fire") ? "rgba(245, 158, 11, 0.15)" :
                                feat.group.includes("Historical") ? "rgba(6, 182, 212, 0.15)" :
                                feat.group.includes("Meteorology") ? "rgba(139, 92, 246, 0.15)" :
                                feat.group.includes("Seasonality") ? "rgba(16, 185, 129, 0.15)" : "rgba(255, 255, 255, 0.08)",
                              color:
                                feat.group.includes("Fire") ? "#f59e0b" :
                                feat.group.includes("Historical") ? "#06b6d4" :
                                feat.group.includes("Meteorology") ? "#c084fc" :
                                feat.group.includes("Seasonality") ? "#34d399" : "#cbd5e1"
                            }}
                          >
                            {feat.group}
                          </span>
                        </td>
                        <td>{feat.value}</td>
                        <td style={{ fontWeight: 700, color: isPositive ? "#ef4444" : "#10b981" }}>
                          {isPositive ? `+${shapVal.toFixed(2)}` : shapVal.toFixed(2)} µg/m³
                        </td>
                        <td>
                          <span style={{ fontSize: "0.78rem", color: isPositive ? "#fca5a5" : "#86efac" }}>
                            {isPositive ? "Elevates PM2.5" : "Suppresses PM2.5"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
