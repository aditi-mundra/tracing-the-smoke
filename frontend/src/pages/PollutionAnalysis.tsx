import React, { useEffect, useState, useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { BarChart3, TrendingUp, Calendar, AlertCircle, Filter, Info } from "lucide-react";
import { fetchPollution, fetchFires, fetchWeather } from "../services/api";

export default function PollutionAnalysis() {
  const [pollutionData, setPollutionData] = useState<any[]>([]);
  const [fireData, setFireData] = useState<any[]>([]);
  const [weatherData, setWeatherData] = useState<any[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(2024);
  const [harvestOnly, setHarvestOnly] = useState<boolean>(false);
  const [lagDays, setLagDays] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchPollution(selectedYear), fetchFires(selectedYear), fetchWeather(selectedYear)])
      .then(([poll, fires, weather]) => {
        setPollutionData(poll || []);
        setFireData(fires || []);
        setWeatherData(weather || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [selectedYear]);

  // Filter by post-monsoon harvest season (Oct 15 - Nov 30) if toggled
  const filteredData = useMemo(() => {
    let pList = [...pollutionData];
    let fList = [...fireData];

    if (harvestOnly) {
      pList = pList.filter((d) => {
        const parts = (d.date_str || "").split("-");
        if (parts.length < 3) return false;
        const m = parseInt(parts[1], 10);
        const day = parseInt(parts[2], 10);
        return (m === 10 && day >= 15) || m === 11;
      });
      const allowedDates = new Set(pList.map((d) => d.date_str));
      fList = fList.filter((f) => allowedDates.has(f.date_str));
    }

    return { pList, fList };
  }, [pollutionData, fireData, harvestOnly]);

  const dates = filteredData.pList.map((d) => d.date_str);
  const pm25 = filteredData.pList.map((d) => d.delhi_daily_pm25_ugm3);
  const stationCounts = filteredData.pList.map((d) => d.active_station_count || 34);
  const upwindFRP = filteredData.fList.map((f) => f.fire_upwind_weighted_frp || 0);

  // Compute Pearson Correlation dynamically with lag
  const correlationInfo = useMemo(() => {
    const pairs: [number, number][] = [];
    const n = Math.min(pm25.length, upwindFRP.length);
    for (let i = lagDays; i < n; i++) {
      const frpVal = upwindFRP[i - lagDays];
      const pmVal = pm25[i];
      if (typeof frpVal === "number" && typeof pmVal === "number" && !isNaN(frpVal) && !isNaN(pmVal)) {
        pairs.push([frpVal, pmVal]);
      }
    }
    if (pairs.length < 10) return { r: 0, count: pairs.length, pairs };

    const nPairs = pairs.length;
    const sumX = pairs.reduce((acc, p) => acc + p[0], 0);
    const sumY = pairs.reduce((acc, p) => acc + p[1], 0);
    const meanX = sumX / nPairs;
    const meanY = sumY / nPairs;

    let num = 0;
    let denX = 0;
    let denY = 0;
    for (const [x, y] of pairs) {
      const dx = x - meanX;
      const dy = y - meanY;
      num += dx * dy;
      denX += dx * dx;
      denY += dy * dy;
    }
    const denom = Math.sqrt(denX * denY);
    const r = denom > 0 ? num / denom : 0;
    return { r, count: nPairs, pairs };
  }, [pm25, upwindFRP, lagDays]);

  // Dual-Axis Chart Options
  const timeSeriesOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1e293b",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#f8fafc" },
      formatter: (params: any[]) => {
        let res = `<b>${params[0]?.axisValue}</b><br/>`;
        params.forEach((p) => {
          res += `${p.marker} ${p.seriesName}: <b>${p.value}</b><br/>`;
        });
        return res;
      }
    },
    legend: {
      data: ["Delhi PM2.5 (µg/m³)", "Upwind Fire FRP (MW)"],
      textStyle: { color: "#94a3b8" },
      top: 0
    },
    grid: { left: "55", right: "60", top: "45", bottom: "35" },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: { color: "#94a3b8", fontSize: 11 }
    },
    yAxis: [
      {
        type: "value",
        name: "PM2.5 (µg/m³)",
        nameTextStyle: { color: "#06b6d4", fontSize: 11 },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
        axisLabel: { color: "#94a3b8" }
      },
      {
        type: "value",
        name: "Upwind FRP (MW)",
        nameTextStyle: { color: "#f59e0b", fontSize: 11 },
        splitLine: { show: false },
        axisLabel: { color: "#f59e0b" }
      }
    ],
    series: [
      {
        name: "Delhi PM2.5 (µg/m³)",
        type: "line",
        data: pm25,
        smooth: true,
        lineStyle: { color: "#06b6d4", width: 2 },
        markLine: {
          symbol: "none",
          data: [
            {
              yAxis: 250,
              lineStyle: { color: "#ef4444", type: "dashed", width: 1.5 },
              label: {
                position: "insideEndTop",
                formatter: "Study Severe Threshold (250 µg/m³)",
                color: "#ef4444",
                fontSize: 10
              }
            }
          ]
        }
      },
      {
        name: "Upwind Fire FRP (MW)",
        type: "bar",
        yAxisIndex: 1,
        data: upwindFRP,
        itemStyle: { color: "rgba(245, 158, 11, 0.45)", borderRadius: [3, 3, 0, 0] }
      }
    ]
  };

  // Scatter plot
  const scatterOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "#1e293b",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#f8fafc" },
      formatter: (p: any) => `Upwind FRP (lag ${lagDays}d): <b>${p.value[0]} MW</b><br/>Delhi PM2.5: <b>${p.value[1]} µg/m³</b>`
    },
    grid: { left: "55", right: "25", top: "30", bottom: "40" },
    xAxis: {
      name: `Upwind Weighted FRP (MW) [Lag ${lagDays}d]`,
      nameLocation: "middle",
      nameGap: 25,
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      axisLabel: { color: "#94a3b8" }
    },
    yAxis: {
      name: "PM2.5 (µg/m³)",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      axisLabel: { color: "#94a3b8" }
    },
    series: [
      {
        type: "scatter",
        symbolSize: 8,
        data: correlationInfo.pairs,
        itemStyle: { color: "#06b6d4", opacity: 0.75 }
      }
    ]
  };

  const avgRepStations = stationCounts.length > 0 ? (stationCounts.reduce((a, b) => a + b, 0) / stationCounts.length).toFixed(1) : "34.0";
  const severeDaysCount = pm25.filter((v) => v >= 250).length;

  return (
    <div>
      <div className="page-header" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Historical Pollution & Episode Analysis</h1>
          <p className="page-subtitle">
            Temporal patterns, station-level coverage, seasonal trends, and empirical fire activity correlation
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.4rem", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Year:</span>
          {[2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025].map((yr) => (
            <button
              key={yr}
              className={`btn ${selectedYear === yr ? "btn-primary" : "btn-outline"}`}
              style={{ padding: "0.25rem 0.6rem", fontSize: "0.8rem" }}
              onClick={() => setSelectedYear(yr)}
            >
              {yr}
            </button>
          ))}
        </div>
      </div>

      {/* Filter and Lag Control Bar */}
      <div className="card" style={{ marginBottom: "1.25rem", display: "flex", gap: "1.5rem", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Filter size={16} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Season Filter:</span>
          <button
            className={`btn ${!harvestOnly ? "btn-primary" : "btn-outline"}`}
            style={{ padding: "0.25rem 0.6rem", fontSize: "0.8rem" }}
            onClick={() => setHarvestOnly(false)}
          >
            Full Year ({selectedYear})
          </button>
          <button
            className={`btn ${harvestOnly ? "btn-primary" : "btn-outline"}`}
            style={{ padding: "0.25rem 0.6rem", fontSize: "0.8rem" }}
            onClick={() => setHarvestOnly(true)}
          >
            Post-Monsoon Harvest Window (Oct 15 – Nov 30)
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Correlation Lag:</span>
          {[0, 1, 2].map((lag) => (
            <button
              key={lag}
              className={`btn ${lagDays === lag ? "btn-primary" : "btn-outline"}`}
              style={{ padding: "0.25rem 0.6rem", fontSize: "0.8rem" }}
              onClick={() => setLagDays(lag)}
            >
              Lag {lag}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "2rem", color: "var(--text-secondary)" }}>Loading pollution analytics...</div>
      ) : (
        <>
          {/* Main Dual-Axis Chart */}
          <div className="chart-box">
            <div className="chart-header">
              <div>
                <div className="chart-title">
                  Daily Delhi PM2.5 (µg/m³) vs Upwind Fire FRP (MW) — {selectedYear} {harvestOnly ? "(Oct 15 – Nov 30 Harvest Window)" : "(Full Year)"}
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Empirical alignment showing upwind biomass burning pulses and subsequent PM2.5 accumulation under winter meteorology
                </div>
              </div>
            </div>
            <ReactECharts option={timeSeriesOption} style={{ height: 350 }} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "1.25rem" }}>
            {/* Scatter Correlation */}
            <div className="chart-box" style={{ marginBottom: 0 }}>
              <div className="chart-header">
                <div>
                  <div className="chart-title">
                    Empirical Correlation: Upwind Fire FRP vs Delhi PM2.5 (r = {correlationInfo.r.toFixed(3)})
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    Calculated over N = {correlationInfo.count} matched days with Lag {lagDays}d (statistical association, not causal attribution)
                  </div>
                </div>
              </div>
              <ReactECharts option={scatterOption} style={{ height: 280 }} />
            </div>

            {/* Station Coverage and Data Quality */}
            <div className="card">
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <AlertCircle size={18} color="var(--accent-cyan)" />
                <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Station Network Completeness ({selectedYear})</h3>
              </div>
              <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
                Citywide target PM2.5 is synthesized from <b>40 eligible CAAQM stations in Delhi NCT</b> (out of 53 discovered regional NCR records).
                Daily active reporting stations range from 10 to 38 (mean: 34 stations), providing robust citywide spatial representation without isolated sensor bias.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "8px" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Average Active Stations</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {avgRepStations} / 40 eligible
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "2px" }}>Delhi NCT network</div>
                </div>
                <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "8px" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Study Severe Days (≥ 250 µg/m³)</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--accent-red)" }}>
                    {severeDaysCount} Days
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "2px" }}>in selected filter window</div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
