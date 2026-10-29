import React, { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import {
  Radio,
  RefreshCw,
  Wind,
  Layers,
  Activity,
  AlertTriangle,
  ShieldAlert,
  Compass,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
  TrendingDown,
  Info
} from "lucide-react";
import { fetchLiveTelemetry, triggerLiveRefresh } from "../services/api";

export default function LiveMonitoring() {
  const [telemetry, setTelemetry] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");

  const loadTelemetry = async (force: boolean = false) => {
    if (force) setRefreshing(true);
    else setLoading(true);
    setFetchError(null);

    try {
      const data = force ? await triggerLiveRefresh() : await fetchLiveTelemetry();
      setTelemetry(data);
    } catch (err: any) {
      console.error("Failed to load live telemetry:", err);
      setFetchError(err?.message || "Network error — backend unreachable");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadTelemetry();
  }, []);

  // Auto-refresh interval (every 60s)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadTelemetry(false);
    }, 60000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  if (loading && !telemetry) {
    return (
      <div style={{ padding: "3rem", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <RefreshCw size={20} className="spin" />
        <span>Connecting to live atmospheric telemetry and CPCB station feed...</span>
      </div>
    );
  }

  // Show error card if fetch failed and no cached telemetry exists
  if (!telemetry && fetchError) {
    return (
      <div style={{ padding: "2rem" }}>
        <div style={{
          background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.35)",
          borderRadius: "10px", padding: "1.5rem 1.75rem"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.75rem" }}>
            <AlertTriangle size={20} color="#f87171" />
            <span style={{ fontWeight: 700, color: "#f87171", fontSize: "1rem" }}>Backend Unreachable</span>
          </div>
          <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
            The live telemetry service could not connect to the FastAPI backend.
          </p>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            <b>Error:</b> {fetchError}
          </p>
          <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.7 }}>
            <b>To fix this:</b>
            <ul style={{ marginTop: "0.4rem", paddingLeft: "1.25rem" }}>
              <li>If running <b>locally</b>: start the backend with <code style={{ background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: "3px" }}>uvicorn backend.app.main:app --host 0.0.0.0 --port 8000</code></li>
              <li>If using the <b>Vercel deployment</b>: set the <code style={{ background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: "3px" }}>VITE_API_BASE</code> environment variable in Vercel dashboard to your Render backend URL, then redeploy.</li>
            </ul>
          </div>
          <button
            onClick={() => loadTelemetry()}
            style={{
              marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.4rem",
              background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.4)",
              color: "#f87171", padding: "0.45rem 1rem", borderRadius: "7px",
              fontWeight: 600, fontSize: "0.83rem", cursor: "pointer"
            }}
          >
            <RefreshCw size={14} /> Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const weather = telemetry?.weather || {};
  const transport = telemetry?.transport_analysis || {};
  const aqi = telemetry?.air_quality_telemetry || {};
  const hourly = telemetry?.hourly_forecast_24h || [];
  const stations = telemetry?.stations_telemetry || [];

  const isSevere = aqi.is_severe_episode;
  const isUpwind = transport.is_upwind_corridor_active;

  // 24-Hour Forecast Chart Options
  const chartHours = hourly.map((h: any) => h.time);
  const chartPm25 = hourly.map((h: any) => h.forecast_pm25);
  const chartBlh = hourly.map((h: any) => h.boundary_layer_height_m);
  const chartVent = hourly.map((h: any) => h.ventilation_index);

  const hourlyChartOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "#0f172a",
      borderColor: "rgba(255,255,255,0.15)",
      textStyle: { color: "#f8fafc" },
      formatter: (params: any[]) => {
        let res = `<b>Time: ${params[0]?.axisValue}</b><br/>`;
        params.forEach((p) => {
          res += `${p.marker} ${p.seriesName}: <b>${p.value}</b><br/>`;
        });
        return res;
      }
    },
    legend: {
      data: ["Forecast PM2.5 (µg/m³)", "Boundary Layer Height (m)", "Ventilation Index (m²/s)"],
      textStyle: { color: "#94a3b8" },
      top: 5
    },
    grid: { left: "50", right: "50", top: "45", bottom: "35" },
    xAxis: {
      type: "category",
      data: chartHours,
      axisLabel: { color: "#94a3b8", fontSize: 11 }
    },
    yAxis: [
      {
        type: "value",
        name: "PM2.5 (µg/m³)",
        nameTextStyle: { color: "#06b6d4" },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
        axisLabel: { color: "#06b6d4" }
      },
      {
        type: "value",
        name: "BLH / Ventilation",
        nameTextStyle: { color: "#8b5cf6" },
        splitLine: { show: false },
        axisLabel: { color: "#8b5cf6" }
      }
    ],
    series: [
      {
        name: "Forecast PM2.5 (µg/m³)",
        type: "line",
        smooth: true,
        data: chartPm25,
        lineStyle: { width: 3, color: "#06b6d4" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(6, 182, 212, 0.35)" },
              { offset: 1, color: "rgba(6, 182, 212, 0.0)" }
            ]
          }
        },
        markLine: {
          symbol: "none",
          data: [
            {
              yAxis: 250,
              lineStyle: { color: "#ef4444", type: "dashed", width: 2 },
              label: { position: "insideEndTop", formatter: "Severe Alert (≥250)", color: "#ef4444" }
            }
          ]
        }
      },
      {
        name: "Boundary Layer Height (m)",
        type: "line",
        yAxisIndex: 1,
        smooth: true,
        data: chartBlh,
        lineStyle: { width: 2, color: "#8b5cf6", type: "dotted" }
      },
      {
        name: "Ventilation Index (m²/s)",
        type: "line",
        yAxisIndex: 1,
        smooth: true,
        data: chartVent,
        lineStyle: { width: 1.5, color: "#10b981" }
      }
    ]
  };

  // Filter stations
  const filteredStations = stations.filter((s: any) =>
    (s.station_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (s.district || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.35rem" }}>
            <span className="pulse-indicator emerald">
              <span className="pulse-dot" />
              <span>LIVE TELEMETRY STREAM</span>
            </span>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              Synced: {telemetry?.query_time}
            </span>
          </div>
          <h1 className="page-title">Live Real-Time Atmospheric Monitoring</h1>
          <p className="page-subtitle">
            Autonomous operational telemetry ingesting live Open-Meteo NWP meteorology, computing boundary layer dispersion dynamics, and generating real-time air quality forecasts.
          </p>
        </div>

        {/* Live Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.82rem", color: "var(--text-secondary)", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Auto-Sync (60s)</span>
          </label>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => loadTelemetry(true)}
            disabled={refreshing}
            style={{ gap: "0.45rem" }}
          >
            <RefreshCw size={14} className={refreshing ? "spin" : ""} />
            <span>{refreshing ? "Syncing..." : "Sync Live Now"}</span>
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="card-grid" style={{ marginBottom: "1.25rem" }}>
        {/* PM2.5 Live Card */}
        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Live Estimated PM2.5</span>
            <div className="kpi-icon-wrap">
              <Activity size={16} color="var(--accent-cyan)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: isSevere ? "#f87171" : "#38bdf8" }}>
            {aqi.live_estimated_pm25 ?? "—"} <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--text-muted)" }}>µg/m³</span>
          </div>
          <div className="kpi-subtitle">
            <span className={`badge ${isSevere ? "badge-severe" : "badge-caution"}`} style={{ fontSize: "0.72rem" }}>
              {aqi.aqi_category}
            </span>
          </div>
        </div>

        {/* Wind Vector Card */}
        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">10m Wind & Advection</span>
            <div className="kpi-icon-wrap">
              <Wind size={16} color="var(--accent-teal)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-teal)" }}>
            {weather.wind_speed_ms ?? "—"} <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--text-muted)" }}>m/s</span>
          </div>
          <div className="kpi-subtitle">
            Bearing: <b>{weather.wind_direction_deg}°</b> ({transport.wind_direction_label})
          </div>
        </div>

        {/* Boundary Layer & Ventilation Card */}
        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Boundary Layer (BLH)</span>
            <div className="kpi-icon-wrap">
              <Layers size={16} color="var(--accent-purple)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-purple)" }}>
            {weather.boundary_layer_height_m ?? "—"} <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--text-muted)" }}>m</span>
          </div>
          <div className="kpi-subtitle">
            Ventilation Index: <b>{weather.ventilation_index} m²/s</b>
          </div>
        </div>

        {/* Advection Alignment Card */}
        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Smoke Corridor Alignment</span>
            <div className="kpi-icon-wrap">
              <Compass size={16} color={isUpwind ? "var(--accent-amber)" : "var(--accent-emerald)"} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: isUpwind ? "var(--accent-amber)" : "var(--accent-emerald)" }}>
            {(transport.advection_alignment_coefficient * 100).toFixed(0)}%
          </div>
          <div className="kpi-subtitle">
            Transit time: <b>~{transport.estimated_plume_transit_hours} hrs</b> to Delhi
          </div>
        </div>
      </div>

      {/* Early Warning Advisory & Inversion Banner */}
      <div
        className="card"
        style={{
          marginBottom: "1.5rem",
          borderLeft: `4px solid ${transport.smoke_transport_risk === "EMERGENCY" ? "#ef4444" : transport.smoke_transport_risk === "HIGH" ? "#f59e0b" : "#10b981"}`,
          padding: "1.15rem 1.4rem"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
              <ShieldAlert size={18} color={transport.smoke_transport_risk === "EMERGENCY" ? "#ef4444" : "#f59e0b"} />
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)" }}>
                Live Early Warning Risk: {transport.smoke_transport_risk} ADVECTION RISK
              </h3>
            </div>
            <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5, maxWidth: "900px" }}>
              {transport.inversion_description}. {transport.is_upwind_corridor_active
                ? "Winds from the north-west corridor are actively funneling biomass emissions from the Punjab–Haryana agricultural belt directly toward the Delhi receptor."
                : "Wind trajectory is currently deflected from the primary stubble burning corridor."}
            </p>
          </div>

          <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "0.6rem 0.85rem" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Recommended Action</div>
            <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--accent-amber)", marginTop: "2px" }}>
              {aqi.grap_recommendation}
            </div>
          </div>
        </div>
      </div>

      {/* 24-Hour Forward Forecast Chart */}
      <div className="chart-box">
        <div className="chart-header">
          <div>
            <div className="chart-title">24-Hour Ahead Hourly Trajectory & Atmospheric Ventilation Forecast</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              Physics-guided ML prediction combining numerical weather boundary layer dynamics and wind advection vectors
            </div>
          </div>
          <span className="badge badge-cyan">Model: XGBoost Exp C (NWP Hourly Integration)</span>
        </div>
        <ReactECharts option={hourlyChartOption} style={{ height: 350 }} />
      </div>

      {/* Live Station Network Telemetry Table */}
      <div className="chart-box">
        <div className="chart-header">
          <div>
            <div className="chart-title">Delhi NCT CAAQM Station Grid Telemetry ({filteredStations.length} Active Sites)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              Current ambient monitoring telemetry across all 40 verified continuous ambient air quality stations
            </div>
          </div>

          {/* Search box */}
          <input
            type="text"
            placeholder="Filter stations or districts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
              color: "#f8fafc",
              padding: "0.4rem 0.75rem",
              borderRadius: "6px",
              fontSize: "0.82rem",
              fontFamily: "inherit",
              outline: "none",
              minWidth: "220px"
            }}
          />
        </div>

        <div className="table-container" style={{ maxHeight: "380px" }}>
          <table>
            <thead>
              <tr>
                <th>Station ID</th>
                <th>Station Name</th>
                <th>District</th>
                <th>Coordinates</th>
                <th>Live PM2.5</th>
                <th>Air Quality Category</th>
                <th>Network Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredStations.map((st: any) => (
                <tr key={st.station_id}>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--accent-cyan)" }}>
                    {st.station_id}
                  </td>
                  <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>{st.station_name}</td>
                  <td>{st.district}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                    {st.latitude?.toFixed(4)}°N, {st.longitude?.toFixed(4)}°E
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: st.live_pm25 >= 250 ? "#f87171" : st.live_pm25 >= 121 ? "#fbbf24" : "#34d399" }}>
                    {st.live_pm25} µg/m³
                  </td>
                  <td>
                    <span className={`badge ${st.live_pm25 >= 250 ? "badge-severe" : st.live_pm25 >= 121 ? "badge-caution" : "badge-good"}`} style={{ fontSize: "0.7rem" }}>
                      {st.category}
                    </span>
                  </td>
                  <td>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "#34d399", fontSize: "0.78rem" }}>
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981" }} />
                      Operational
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
