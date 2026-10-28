import React, { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { Activity, Flame, Wind, Layers, AlertTriangle, ShieldCheck, TrendingUp, Info, Radio } from "lucide-react";
import { fetchOverview, fetchPollution, fetchLiveTelemetry } from "../services/api";
import CalendarDateSelector, { DEFAULT_SHORTCUTS } from "../components/CalendarDateSelector";

const TODAY = new Date().toISOString().split("T")[0];

export default function EnvironmentalOverview() {
  const [selectedDate, setSelectedDate] = useState("2024-11-18");
  const [isLiveMode, setIsLiveMode] = useState<boolean>(false);
  const [liveTelemetry, setLiveTelemetry] = useState<any>(null);
  const [overview, setOverview] = useState<any>(null);
  const [pollutionData, setPollutionData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateError, setDateError] = useState<string | null>(null);

  useEffect(() => {
    if (isLiveMode) {
      // In live mode, fetch live telemetry from Open-Meteo
      setLoading(true);
      setDateError(null);
      fetchLiveTelemetry()
        .then((data) => {
          setLiveTelemetry(data);
          // Build an overview-compatible shape from live telemetry
          const liveOverview = {
            date_str: TODAY,
            is_historical_replay: false,
            observed_pm25: data?.air_quality_telemetry?.live_estimated_pm25 ?? null,
            episode_label: data?.air_quality_telemetry?.grap_recommendation ?? "Live Estimate",
            fire_count_total: null,
            fire_count_upwind: null,
            fire_count_punjab: null,
            fire_count_haryana: null,
            wind_speed: data?.weather?.wind_speed_ms ?? null,
            prevailing_wind_direction: data?.weather?.wind_direction_deg ?? null,
            boundary_layer_height: data?.weather?.boundary_layer_height_m ?? null,
            ventilation_index: data?.weather?.ventilation_index ?? null,
          };
          setOverview(liveOverview);
        })
        .catch((err) => {
          console.warn("live telemetry fetch error:", err);
          setDateError("Live telemetry fetch failed. Check your network connection.");
        })
        .finally(() => setLoading(false));
      return;
    }
    setLoading(true);
    setDateError(null);
    fetchOverview(selectedDate)
      .then((data) => {
        setOverview(data);
        setDateError(null);
      })
      .catch((err) => {
        console.warn("fetchOverview error for date:", selectedDate, err);
        setDateError(`No continuous CPCB / ERA5 multi-source record available for '${selectedDate}'. Valid historical range spans 2018-01-01 to 2025-06-02.`);
      })
      .finally(() => setLoading(false));
  }, [selectedDate, isLiveMode]);

  useEffect(() => {
    fetchPollution(2024)
      .then((poll) => {
        if (poll && poll.length > 0) setPollutionData(poll);
      })
      .catch((err) => console.error("fetchPollution error:", err));
  }, []);

  const isSevere = (overview?.observed_pm25 ?? 0) >= 250;
  const isHigh = (overview?.observed_pm25 ?? 0) >= 120 && (overview?.observed_pm25 ?? 0) < 250;

  // Chart options
  const dates = pollutionData.map((d) => d.date_str);
  const pm25Values = pollutionData.map((d) => d.delhi_daily_pm25_ugm3);

  const chartOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1e293b",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#f8fafc" },
      formatter: "{b}<br/>Citywide PM2.5: <b>{c} µg/m³</b>"
    },
    grid: { left: "45", right: "20", top: "30", bottom: "35" },
    xAxis: {
      type: "category",
      data: dates,
      axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
      axisLabel: { color: "#94a3b8", fontSize: 11 }
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
        name: "Observed PM2.5",
        type: "line",
        data: pm25Values,
        smooth: true,
        lineStyle: { width: 2.5, color: "#06b6d4" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(6, 182, 212, 0.4)" },
              { offset: 1, color: "rgba(6, 182, 212, 0.0)" }
            ]
          }
        },
        markLine: {
          symbol: "none",
          data: [
            {
              yAxis: 250,
              name: "Study Severe Threshold",
              lineStyle: { color: "#ef4444", type: "dashed", width: 2 },
              label: { position: "insideEndTop", formatter: "Study Severe Threshold: PM2.5 ≥ 250 µg/m³", color: "#ef4444" }
            }
          ]
        }
      }
    ]
  };

  return (
    <div>
      <div className="page-header" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Historical Multi-Source Environmental Intelligence</h1>
          <p className="page-subtitle">
            Retrospective ML analysis of Delhi PM2.5, Punjab–Haryana agricultural fires, and atmospheric transport (2018–2024 full study, partial 2025 CPCB coverage)
          </p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
          {/* Live Mode Toggle */}
          <button
            onClick={() => setIsLiveMode((v) => !v)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              padding: "0.4rem 0.9rem",
              borderRadius: "8px",
              border: isLiveMode ? "1px solid #ef4444" : "1px solid rgba(255,255,255,0.15)",
              background: isLiveMode ? "rgba(239, 68, 68, 0.18)" : "rgba(255,255,255,0.06)",
              color: isLiveMode ? "#f87171" : "var(--text-secondary)",
              fontWeight: 700,
              fontSize: "0.82rem",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
          >
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: isLiveMode ? "#ef4444" : "#64748b", flexShrink: 0 }} />
            {isLiveMode ? "🔴 LIVE — TODAY" : "📅 Historical Mode"}
          </button>
          <span className="badge badge-cyan">{isLiveMode ? "Live: Open-Meteo NWP" : "Study: 2018–2024 Verified"}</span>
          <span className={`badge ${isSevere ? "badge-severe" : isHigh ? "badge-caution" : "badge-good"}`}>
            {isSevere ? "Severe Episode (≥ 250 µg/m³)" : isHigh ? "Very Poor / Elevated Smog" : "Moderate Air Quality"}
          </span>
        </div>
      </div>

      {/* Live mode status bar */}
      {isLiveMode && liveTelemetry && (
        <div style={{ background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "8px", padding: "0.65rem 1rem", marginBottom: "1.25rem", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "1rem", fontSize: "0.82rem" }}>
          <span style={{ color: "#f87171", fontWeight: 700 }}>🔴 LIVE OPERATIONAL — {TODAY}</span>
          <span style={{ color: "#94a3b8" }}>Wind: <b style={{ color: "#22d3ee" }}>{liveTelemetry.weather?.wind_speed_ms} m/s @ {liveTelemetry.weather?.wind_direction_deg}°</b></span>
          <span style={{ color: "#94a3b8" }}>BLH: <b style={{ color: "#a78bfa" }}>{liveTelemetry.weather?.boundary_layer_height_m} m</b></span>
          <span style={{ color: "#94a3b8" }}>Risk: <b style={{ color: "#f87171" }}>{liveTelemetry.transport_analysis?.smoke_transport_risk}</b></span>
          <span style={{ color: "#94a3b8" }}>GRAP: <b style={{ color: "#fb923c" }}>{liveTelemetry.air_quality_telemetry?.grap_recommendation?.split("(")[0]?.trim()}</b></span>
        </div>
      )}

      {/* Interactive Calendar Date Picker & Shortcuts */}
      {!isLiveMode && (
        <div className="card" style={{ marginBottom: "1.25rem", padding: "0.85rem 1.15rem" }}>
          <CalendarDateSelector
            value={selectedDate}
            onChange={setSelectedDate}
            minDate="2018-01-01"
            maxDate="2025-12-31"
            label="Observation Date"
            helperText="Pick any calendar date across the continuous historical study period (2018-01-01 to 2025-12-31) or use a quick demonstration shortcut."
            shortcuts={DEFAULT_SHORTCUTS}
          />
        </div>
      )}

      {/* Date Banner Note or Error State */}
      {dateError ? (
        <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "8px", padding: "0.75rem 1rem", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <AlertTriangle size={18} color="var(--accent-red)" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: "0.84rem", color: "#fca5a5" }}>
            {dateError}
          </span>
        </div>
      ) : isLiveMode ? (
        <div style={{ background: "rgba(239, 68, 68, 0.06)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "8px", padding: "0.65rem 1rem", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <Radio size={16} color="#f87171" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: "0.82rem", color: "#cbd5e1" }}>
            Live telemetry for <b style={{ color: "#f87171" }}>{TODAY} (Today)</b> sourced from <b>Open-Meteo High-Resolution NWP</b>. PM2.5 is a real-time physics-guided estimate (not a CPCB measurement).
            GRAP Stage: <b style={{ color: "#fb923c" }}>{overview?.episode_label || "Calculating…"}</b>
          </span>
        </div>
      ) : (
        <div style={{ background: "rgba(6, 182, 212, 0.08)", border: "1px solid rgba(6, 182, 212, 0.2)", borderRadius: "8px", padding: "0.65rem 1rem", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <Info size={16} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: "0.82rem", color: "#cbd5e1" }}>
            Displaying historical multi-source snapshot for <b>{overview?.date_str || selectedDate}</b> ({overview?.is_historical_replay ? "Historical Data Archive" : "Observed Snapshot"}).
            Target status: <b style={{ color: isSevere ? "#f87171" : isHigh ? "#fbbf24" : "#34d399" }}>{overview?.episode_label || (isSevere ? "Study Severe Episode" : "Non-Severe Observation")}</b>.
          </span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="card-grid">
        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Observed Citywide PM2.5</span>
            <div className="kpi-icon-wrap">
              <Activity size={16} color="var(--accent-cyan)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: isSevere ? "var(--accent-red)" : isHigh ? "var(--accent-amber)" : "var(--accent-cyan)" }}>
            {overview?.observed_pm25 ?? "—"} <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--text-muted)" }}>µg/m³</span>
          </div>
          <div className="kpi-subtitle">
            Observed across <b>40 CAAQM stations</b> in Delhi NCT (34–38 active daily)
          </div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Upwind Active Fires</span>
            <div className="kpi-icon-wrap">
              <Flame size={16} color="var(--accent-amber)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-amber)" }}>
            {overview?.fire_count_upwind ?? 0}{" "}
            <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--text-muted)" }}>
              / {overview?.fire_count_total ?? 0} total
            </span>
          </div>
          <div className="kpi-subtitle">
            {overview?.fire_count_punjab ?? 0} Punjab • {overview?.fire_count_haryana ?? 0} Haryana detections (FIRMS B2)
          </div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Transport Wind Speed</span>
            <div className="kpi-icon-wrap">
              <Wind size={16} color="var(--accent-teal)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-teal)" }}>
            {overview?.wind_speed ?? "—"} <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--text-muted)" }}>m/s</span>
          </div>
          <div className="kpi-subtitle">
            Bearing: {overview?.prevailing_wind_direction ?? 315}° ({overview?.prevailing_wind_direction >= 270 && overview?.prevailing_wind_direction <= 360 ? "NW advection corridor" : "regional flow"})
          </div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Boundary Layer Height</span>
            <div className="kpi-icon-wrap">
              <Layers size={16} color="var(--accent-purple)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-purple)" }}>
            {overview?.boundary_layer_height ?? "—"} <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--text-muted)" }}>m</span>
          </div>
          <div className="kpi-subtitle">
            Ventilation Index: <b>{overview?.ventilation_index ?? "—"} m²/s</b> (dispersion capacity)
          </div>
        </div>
      </div>

      {/* Main Chart */}
      <div className="chart-box">
        <div className="chart-header">
          <div>
            <div className="chart-title">Delhi Citywide Daily PM2.5 Trend (Held-Out Test Year 2024)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              Full 366-day continuous test series including post-monsoon burning peak and winter inversion with Study Severe-Episode Threshold reference
            </div>
          </div>
        </div>
        <ReactECharts option={chartOption} style={{ height: 340 }} />
      </div>

      {/* System Status / Methodology highlight */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem" }}>
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <ShieldCheck size={18} color="var(--accent-green)" />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 600 }}>Multi-Source Data Provenance</h3>
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            The pipeline ingests verified continuous ambient observations from <b>40 eligible CAAQM stations in Delhi NCT</b> (out of 53 discovered regional NCR records),
            satellite active-fire detections from <b>NASA FIRMS VIIRS S-NPP (375m)</b>, and hourly reanalysis meteorology from <b>ECMWF ERA5</b>.
          </p>
        </div>

        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <TrendingUp size={18} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 600 }}>Chronological ML Evaluation</h3>
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            Models (Ridge, Random Forest, XGBoost, LightGBM) are trained strictly chronologically (Train: 2018–2022, Val: 2023, Test: 2024).
            Best model (Exp C XGBoost) achieves <b>R² = 0.8472</b>, MAE = 17.86 µg/m³ on the complete 366-day 2024 test evaluation.
          </p>
        </div>
      </div>
    </div>
  );
}
