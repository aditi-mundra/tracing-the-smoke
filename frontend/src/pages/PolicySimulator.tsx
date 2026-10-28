import React, { useState, useEffect } from "react";
import ReactECharts from "echarts-for-react";
import {
  Sliders,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  Wind,
  Flame,
  Activity,
  HeartPulse,
  Printer,
  Sparkles,
  RefreshCw,
  Info,
  Layers,
  ArrowRight
} from "lucide-react";
import { fetchCounterfactualSimulation } from "../services/api";
import CalendarDateSelector, { DEFAULT_SHORTCUTS } from "../components/CalendarDateSelector";

export default function PolicySimulator() {
  const [selectedDate, setSelectedDate] = useState<string>("2024-11-18");
  const [punjabAbatement, setPunjabAbatement] = useState<number>(50);
  const [haryanaAbatement, setHaryanaAbatement] = useState<number>(50);
  const [windMultiplier, setWindMultiplier] = useState<number>(1.0);
  const [blhMultiplier, setBlhMultiplier] = useState<number>(1.0);
  const [selectedModel, setSelectedModel] = useState<string>("xgboost");

  const [simulation, setSimulation] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = (
    date = selectedDate,
    pb = punjabAbatement,
    hr = haryanaAbatement,
    w = windMultiplier,
    b = blhMultiplier,
    m = selectedModel
  ) => {
    setLoading(true);
    setError(null);
    fetchCounterfactualSimulation({
      date,
      punjab_abatement_pct: pb,
      haryana_abatement_pct: hr,
      wind_speed_multiplier: w,
      blh_multiplier: b,
      model_name: m
    })
      .then((data) => {
        setSimulation(data);
        setError(null);
      })
      .catch((err) => {
        console.error("Simulation error:", err);
        setError("Unable to compute counterfactual simulation for the selected date.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    runSimulation(selectedDate, punjabAbatement, haryanaAbatement, windMultiplier, blhMultiplier, selectedModel);
  }, [selectedDate, punjabAbatement, haryanaAbatement, windMultiplier, blhMultiplier, selectedModel]);

  // Preset Scenario Handlers
  const applyPreset = (preset: string) => {
    if (preset === "caqm_50") {
      setPunjabAbatement(50);
      setHaryanaAbatement(50);
      setWindMultiplier(1.0);
      setBlhMultiplier(1.0);
    } else if (preset === "zero_burn") {
      setPunjabAbatement(100);
      setHaryanaAbatement(100);
      setWindMultiplier(1.0);
      setBlhMultiplier(1.0);
    } else if (preset === "punjab_focus") {
      setPunjabAbatement(85);
      setHaryanaAbatement(30);
      setWindMultiplier(1.0);
      setBlhMultiplier(1.0);
    } else if (preset === "inversion_shock") {
      setPunjabAbatement(0);
      setHaryanaAbatement(0);
      setWindMultiplier(0.7);
      setBlhMultiplier(0.7);
    } else if (preset === "clean_airshed") {
      setPunjabAbatement(100);
      setHaryanaAbatement(100);
      setWindMultiplier(1.3);
      setBlhMultiplier(1.3);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  // Stacked Bar breakdown chart
  const breakdown = simulation?.source_attribution_breakdown;
  const breakdownChartOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#1e293b",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#f8fafc" },
      formatter: (params: any[]) => {
        let str = `<b>Attribution Breakdown (${simulation?.date})</b><br/>`;
        params.forEach((p) => {
          str += `${p.marker} ${p.seriesName}: <b>${p.value} µg/m³</b><br/>`;
        });
        return str;
      }
    },
    legend: {
      data: ["Punjab Abated", "Haryana Abated", "Meteorology Gain", "Unabated Smoke", "Residual Urban"],
      textStyle: { color: "#94a3b8", fontSize: 11 },
      top: 0
    },
    grid: { left: "30", right: "20", top: "40", bottom: "30", containLabel: true },
    xAxis: {
      type: "category",
      data: ["Baseline", "Simulated"],
      axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
      axisLabel: { color: "#cbd5e1" }
    },
    yAxis: {
      type: "value",
      name: "PM2.5 (µg/m³)",
      nameTextStyle: { color: "#94a3b8", fontSize: 11 },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      axisLabel: { color: "#94a3b8" }
    },
    series: [
      {
        name: "Residual Urban",
        type: "bar",
        stack: "total",
        data: [breakdown?.residual_urban_background_pm25 ?? 0, breakdown?.residual_urban_background_pm25 ?? 0],
        itemStyle: { color: "#f59e0b" }
      },
      {
        name: "Unabated Smoke",
        type: "bar",
        stack: "total",
        data: [
          (breakdown?.unabated_biomass_smoke_pm25 ?? 0) +
            (breakdown?.punjab_abated_pm25_ugm3 ?? 0) +
            (breakdown?.haryana_abated_pm25_ugm3 ?? 0),
          breakdown?.unabated_biomass_smoke_pm25 ?? 0
        ],
        itemStyle: { color: "#ef4444" }
      },
      {
        name: "Punjab Abated",
        type: "bar",
        stack: "total",
        data: [0, -(breakdown?.punjab_abated_pm25_ugm3 ?? 0)],
        itemStyle: { color: "#10b981" }
      },
      {
        name: "Haryana Abated",
        type: "bar",
        stack: "total",
        data: [0, -(breakdown?.haryana_abated_pm25_ugm3 ?? 0)],
        itemStyle: { color: "#06b6d4" }
      }
    ]
  };

  const isSimSevere = (simulation?.simulated_pm25 ?? 0) >= 250;
  const isBaseSevere = (simulation?.baseline_pm25 ?? 0) >= 250;

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Counterfactual Policy Simulator & Airshed Intervention Lab</h1>
          <p className="page-subtitle">
            Simulate regional crop residue burning abatement scenarios and meteorological dispersion shifts to quantify the resulting air quality changes in Delhi NCT.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <span className="badge badge-purple">Physics-Guided Box Model</span>
          <span className="badge badge-cyan">CPCB GRAP Alert Engine</span>
          <button
            onClick={handlePrint}
            className="badge badge-teal"
            style={{
              cursor: "pointer",
              border: "1px solid rgba(20, 184, 166, 0.4)",
              background: "rgba(20, 184, 166, 0.15)",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem"
            }}
            title="Generate printable policy briefing"
          >
            <Printer size={13} />
            <span>Export Policy Briefing</span>
          </button>
        </div>
      </div>

      {/* Date Picker */}
      <div className="card" style={{ marginBottom: "1.25rem", padding: "0.85rem 1.15rem" }}>
        <CalendarDateSelector
          value={selectedDate}
          onChange={setSelectedDate}
          minDate="2018-01-01"
          maxDate="2025-12-31"
          label="Intervention Target Date"
          helperText="Select any historical or held-out test date to evaluate counterfactual intervention efficacy."
          shortcuts={DEFAULT_SHORTCUTS}
        />
      </div>

      {/* Preset Policy Scenarios Quick Bar */}
      <div
        className="card"
        style={{
          marginBottom: "1.25rem",
          padding: "0.85rem 1.15rem",
          display: "flex",
          gap: "0.75rem",
          alignItems: "center",
          flexWrap: "wrap"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", marginRight: "0.5rem" }}>
          <Sparkles size={16} color="var(--accent-purple)" />
          <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text-secondary)" }}>
            Policy Presets:
          </span>
        </div>
        <button
          onClick={() => applyPreset("caqm_50")}
          className="badge badge-cyan"
          style={{ cursor: "pointer", padding: "0.4rem 0.75rem" }}
        >
          CAQM 50% Regional Target
        </button>
        <button
          onClick={() => applyPreset("zero_burn")}
          className="badge badge-teal"
          style={{ cursor: "pointer", padding: "0.4rem 0.75rem" }}
        >
          100% Zero-Burn Elimination
        </button>
        <button
          onClick={() => applyPreset("punjab_focus")}
          className="badge badge-purple"
          style={{ cursor: "pointer", padding: "0.4rem 0.75rem" }}
        >
          Malwa Cluster Intensive (85% PB)
        </button>
        <button
          onClick={() => applyPreset("inversion_shock")}
          className="badge badge-red"
          style={{ cursor: "pointer", padding: "0.4rem 0.75rem" }}
        >
          Winter Inversion Shock (-30% VI)
        </button>
        <button
          onClick={() => applyPreset("clean_airshed")}
          className="badge badge-emerald"
          style={{ cursor: "pointer", padding: "0.4rem 0.75rem" }}
        >
          Optimal Airshed (+30% VI & Zero-Burn)
        </button>
      </div>

      {/* Main Grid: Controls vs Results */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "1.25rem",
          marginBottom: "1.25rem"
        }}
      >
        {/* Left Column: Interactive Policy Sliders */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <Sliders size={18} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0 }}>Intervention Levers</h3>
          </div>

          {/* Punjab Slider */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Punjab Crop Residue Abatement
              </span>
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 700,
                  color: "var(--accent-emerald)",
                  fontFamily: "var(--font-mono)"
                }}
              >
                {punjabAbatement}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={punjabAbatement}
              onChange={(e) => setPunjabAbatement(Number(e.target.value))}
              style={{ width: "100%", accentColor: "var(--accent-emerald)" }}
            />
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
              Targeting Majha, Doaba, and Malwa harvest belts.
            </div>
          </div>

          {/* Haryana Slider */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Haryana Crop Residue Abatement
              </span>
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 700,
                  color: "var(--accent-cyan)",
                  fontFamily: "var(--font-mono)"
                }}
              >
                {haryanaAbatement}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={haryanaAbatement}
              onChange={(e) => setHaryanaAbatement(Number(e.target.value))}
              style={{ width: "100%", accentColor: "var(--accent-cyan)" }}
            />
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
              Targeting Fatehabad, Jind, Sirsa, and Kaithal inner buffer (&lt; 150 km).
            </div>
          </div>

          {/* Wind Speed Multiplier */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Wind Advection Speed Multiplier
              </span>
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 700,
                  color: "var(--accent-purple)",
                  fontFamily: "var(--font-mono)"
                }}
              >
                {windMultiplier.toFixed(2)}x
              </span>
            </div>
            <input
              type="range"
              min={0.5}
              max={2.0}
              step={0.05}
              value={windMultiplier}
              onChange={(e) => setWindMultiplier(Number(e.target.value))}
              style={{ width: "100%", accentColor: "var(--accent-purple)" }}
            />
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
              1.0x = Observed meteorological baseline. Values &lt; 1.0x simulate wind stagnation.
            </div>
          </div>

          {/* Boundary Layer Height Multiplier */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Boundary Layer Height (BLH) Multiplier
              </span>
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 700,
                  color: "var(--accent-teal)",
                  fontFamily: "var(--font-mono)"
                }}
              >
                {blhMultiplier.toFixed(2)}x
              </span>
            </div>
            <input
              type="range"
              min={0.5}
              max={2.0}
              step={0.05}
              value={blhMultiplier}
              onChange={(e) => setBlhMultiplier(Number(e.target.value))}
              style={{ width: "100%", accentColor: "var(--accent-teal)" }}
            />
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
              Governs nocturnal vertical mixing volume.
            </div>
          </div>

          {/* ML Model Architecture Selector */}
          <div>
            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: "0.4rem" }}>
              Inference Model Architecture:
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                width: "100%",
                background: "var(--bg-secondary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-color)",
                padding: "0.45rem 0.65rem",
                borderRadius: "6px",
                fontSize: "0.82rem"
              }}
            >
              <option value="xgboost">XGBoost — Physics Transport (Exp C, R² = 0.8472)</option>
              <option value="lightgbm">LightGBM — Physics Transport (Exp C, R² = 0.8398)</option>
              <option value="random_forest">Random Forest — Non-Linear Ensemble (Exp C, R² = 0.8315)</option>
            </select>
          </div>
        </div>

        {/* Right Column: Real-Time Counterfactual Results */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Top Scorecard Comparison */}
          <div
            className="card"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: "1rem",
              padding: "1.25rem"
            }}
          >
            <div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                Observed Baseline
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "#f87171", fontFamily: "var(--font-mono)" }}>
                {simulation?.baseline_pm25 ?? "—"}{" "}
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>µg/m³</span>
              </div>
              <div style={{ fontSize: "0.78rem", color: isBaseSevere ? "#f87171" : "var(--accent-amber)", marginTop: "2px" }}>
                {simulation?.baseline_grap_stage}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div
                style={{
                  background: "rgba(16, 185, 129, 0.12)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  borderRadius: "8px",
                  padding: "0.5rem 0.85rem",
                  textAlign: "center"
                }}
              >
                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Avoided Pollution
                </div>
                <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--accent-emerald)", fontFamily: "var(--font-mono)" }}>
                  {simulation?.delta_pm25 ?? 0} µg/m³
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--accent-emerald)", fontWeight: 600 }}>
                  ({simulation?.pct_reduction ?? 0}% lower)
                </div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                Simulated Air Quality
              </div>
              <div style={{ fontSize: "1.75rem", fontWeight: 800, color: isSimSevere ? "#f59e0b" : "#10b981", fontFamily: "var(--font-mono)" }}>
                {simulation?.simulated_pm25 ?? "—"}{" "}
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>µg/m³</span>
              </div>
              <div style={{ fontSize: "0.78rem", color: isSimSevere ? "#f59e0b" : "#10b981", marginTop: "2px" }}>
                {simulation?.simulated_grap_stage}
              </div>
            </div>
          </div>

          {/* GRAP Transition Banner */}
          <div
            className="card"
            style={{
              padding: "1rem 1.25rem",
              background: simulation?.avoided_severe_episode
                ? "rgba(16, 185, 129, 0.1)"
                : "rgba(59, 130, 246, 0.08)",
              border: simulation?.avoided_severe_episode
                ? "1px solid rgba(16, 185, 129, 0.3)"
                : "1px solid rgba(59, 130, 246, 0.25)"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", marginBottom: "0.35rem" }}>
              {simulation?.avoided_severe_episode ? (
                <ShieldCheck size={20} color="var(--accent-emerald)" />
              ) : (
                <ShieldAlert size={20} color="var(--accent-cyan)" />
              )}
              <h4 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                Regulatory GRAP Emergency Status
              </h4>
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              <b>Transition:</b> {simulation?.stage_transition}
            </div>
            {simulation?.estimated_avoided_health_impact?.avoided_statutory_school_closures && (
              <div
                style={{
                  marginTop: "0.5rem",
                  fontSize: "0.8rem",
                  color: "var(--accent-emerald)",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "0.35rem"
                }}
              >
                <Sparkles size={14} />
                <span>Intervention successfully de-escalates out of GRAP Stage IV statutory school closure mandate.</span>
              </div>
            )}
          </div>

          {/* Health & Public Welfare Card */}
          <div className="card" style={{ padding: "1rem 1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.75rem" }}>
              <HeartPulse size={18} color="var(--accent-red)" />
              <h4 style={{ fontSize: "0.92rem", fontWeight: 700, margin: 0 }}>Public Health Benefit Estimation</h4>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div style={{ background: "var(--bg-secondary)", padding: "0.65rem 0.85rem", borderRadius: "6px" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Averted ER Visits</div>
                <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--accent-emerald)", fontFamily: "var(--font-mono)" }}>
                  ~{simulation?.estimated_avoided_health_impact?.avoided_emergency_outpatient_visits?.toLocaleString() ?? 0}
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Acute respiratory cases</div>
              </div>
              <div style={{ background: "var(--bg-secondary)", padding: "0.65rem 0.85rem", borderRadius: "6px" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Benefiting Population</div>
                <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
                  33+ Million
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Delhi NCT + NCR Airshed</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Attribution Decomposition Stacked Chart */}
      <div className="card" style={{ marginBottom: "1.25rem", padding: "1.25rem" }}>
        <h4 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.5rem" }}>
          Counterfactual Airshed Mass Balance Breakdown
        </h4>
        <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
          Comparison of baseline observed PM2.5 vs simulated PM2.5 partitioned into regional stubble smoke, urban baseline, and dispersion effects.
        </p>
        <ReactECharts option={breakdownChartOption} style={{ height: "300px", width: "100%" }} />
      </div>

      {/* Policy Conclusions & Caveats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "1.25rem"
        }}
      >
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <Info size={16} color="var(--accent-cyan)" />
            <h4 style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-primary)" }}>
              The "Urban Floor" Policy Reality
            </h4>
          </div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            Even in the radical scenario of <b>100% zero stubble burning in both Punjab and Haryana</b>, Delhi's residual PM2.5 during winter stagnation remains above the 24-hr NAAQS limit (60 µg/m³), hovering between 180 and 320 µg/m³. Regional fire elimination prevents acute 500+ µg/m³ emergencies, but whole-airshed year-round clean air requires domestic, vehicular, and industrial urban reduction.
          </p>
        </div>

        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <Activity size={16} color="var(--accent-amber)" />
            <h4 style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-primary)" }}>
              Airshed Scientific Disclaimer
            </h4>
          </div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            {simulation?.scientific_disclaimer}
          </p>
        </div>
      </div>
    </div>
  );
}
