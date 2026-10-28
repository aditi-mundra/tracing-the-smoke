import React, { useState, useEffect } from "react";
import {
  Flame,
  RefreshCw,
  AlertCircle,
  Info,
  Wind,
  MapPin,
  TrendingDown,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { fetchFireTransportRisk } from "../services/api";

// Dates available in the sample_fire_hotspots.json: 2024-10-01 to 2024-11-30
const FIRE_DATE_SHORTCUTS = [
  { date: "2024-11-18", label: "Nov 18 (Peak Smog)" },
  { date: "2024-11-13", label: "Nov 13 (Post-Diwali)" },
  { date: "2024-11-05", label: "Nov 5" },
  { date: "2024-11-01", label: "Nov 1" },
  { date: "2024-10-25", label: "Oct 25" },
  { date: "2024-10-15", label: "Oct 15 (Early Harvest)" },
  { date: "2024-10-01", label: "Oct 1" },
];

const MIN_FIRE_DATE = "2024-10-01";
const MAX_FIRE_DATE = "2024-11-30";

function getRankColor(rank: number) {
  if (rank === 1) return "#ef4444";
  if (rank === 2) return "#f97316";
  if (rank === 3) return "#f59e0b";
  return "#64748b";
}

function getScoreBar(pct: number) {
  const w = Math.max(2, Math.min(100, pct));
  const color = pct > 30 ? "#ef4444" : pct > 15 ? "#f97316" : "#f59e0b";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
      <div style={{
        width: "80px", height: "6px",
        background: "rgba(255,255,255,0.08)",
        borderRadius: "3px", overflow: "hidden", flexShrink: 0
      }}>
        <div style={{
          width: `${w}%`, height: "100%",
          background: color, borderRadius: "3px"
        }} />
      </div>
      <span style={{ fontSize: "0.78rem", color, fontFamily: "var(--font-mono)", minWidth: "42px" }}>
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

export default function FireTransportRisk() {
  const [selectedDate, setSelectedDate] = useState("2024-11-18");
  const [lookbackDays, setLookbackDays] = useState(3);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showNotes, setShowNotes] = useState(false);

  const runRanking = (date = selectedDate, lb = lookbackDays) => {
    setLoading(true);
    setError(null);
    fetchFireTransportRisk({ date, lookback_days: lb })
      .then(data => {
        setResult(data);
      })
      .catch(err => {
        setError(err.message || "Failed to rank fire clusters.");
        setResult(null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    runRanking(selectedDate, lookbackDays);
  }, []);

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedDate(e.target.value);
  };

  const handleShortcut = (date: string) => {
    setSelectedDate(date);
    runRanking(date, lookbackDays);
  };

  const handleLookback = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLookbackDays(Number(e.target.value));
  };

  const clusters = result?.clusters ?? [];
  const isWindFree = result?.ranking_basis === "wind_free" || !result?.ranking_basis?.includes("wind_aware");

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Fire Transport Risk Ranking</h1>
          <p className="page-subtitle">
            Relative ranking of Punjab–Haryana fire clusters by their potential transport relevance to Delhi.
            Ranked by FRP × distance-decay weight (wind-free, since no daily wind observations are available for the sample data).
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <span className="badge badge-amber">VIIRS S-NPP Sample Data</span>
          <span className="badge badge-cyan">Wind-Free Ranking</span>
          <span className="badge badge-purple">Oct–Nov 2024</span>
        </div>
      </div>

      {/* Methodology Explanation */}
      <div className="card" style={{ marginBottom: "1.25rem", padding: "1rem 1.25rem", background: "rgba(6,182,212,0.05)", border: "1px solid rgba(6,182,212,0.2)" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: "0.65rem" }}>
          <Info size={16} color="var(--accent-cyan)" style={{ flexShrink: 0, marginTop: "2px" }} />
          <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            <b style={{ color: "var(--text-primary)" }}>How the ranking works:</b>{" "}
            Each fire detection's <b>Fire Radiative Power (FRP)</b> is weighted by a distance-decay function
            (exp(−d/300km)) relative to Delhi. Detections within the lookback window are aggregated into ~0.5°
            grid cells. Cells are sorted by <b>wind-free score = Σ(FRP × distance_weight)</b>.
            {" "}
            <b style={{ color: "var(--accent-amber)" }}>No wind direction data is used</b> because no daily observed
            wind source is available for this sample dataset — all results are labelled wind-free. Scores are
            unitless indices — compare within one run only, not across dates.
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: "1.25rem", padding: "1rem 1.25rem" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1.25rem", alignItems: "flex-end" }}>
          {/* Date selector */}
          <div style={{ flex: "1 1 200px" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.35rem" }}>
              Target Date
            </label>
            <input
              type="date"
              value={selectedDate}
              min={MIN_FIRE_DATE}
              max={MAX_FIRE_DATE}
              onChange={handleDateChange}
              style={{
                background: "var(--bg-secondary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-color)",
                padding: "0.45rem 0.65rem",
                borderRadius: "6px",
                fontSize: "0.85rem",
                fontFamily: "inherit",
                width: "100%",
                outline: "none"
              }}
            />
            <div style={{ fontSize: "0.73rem", color: "var(--text-muted)", marginTop: "4px" }}>
              Available: Oct 1 – Nov 30, 2024 (sample data)
            </div>
          </div>

          {/* Lookback selector */}
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.35rem" }}>
              Lookback Days
            </label>
            <select
              value={lookbackDays}
              onChange={handleLookback}
              style={{
                background: "var(--bg-secondary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-color)",
                padding: "0.45rem 0.65rem",
                borderRadius: "6px",
                fontSize: "0.85rem",
                fontFamily: "inherit",
                outline: "none"
              }}
            >
              {[0, 1, 2, 3, 5, 7].map(d => (
                <option key={d} value={d}>{d === 0 ? "0 (target date only)" : d === 3 ? `${d} days (default)` : `${d} days`}</option>
              ))}
            </select>
          </div>

          {/* Run button */}
          <button
            onClick={() => runRanking(selectedDate, lookbackDays)}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", gap: "0.45rem",
              background: "rgba(6,182,212,0.15)",
              border: "1px solid rgba(6,182,212,0.4)",
              color: "#22d3ee",
              padding: "0.5rem 1.1rem",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.85rem",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
              transition: "all 0.2s"
            }}
          >
            <RefreshCw size={15} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            {loading ? "Ranking…" : "Calculate Risk Ranking"}
          </button>
        </div>

        {/* Date Shortcuts */}
        <div style={{ marginTop: "0.85rem", display: "flex", flexWrap: "wrap", gap: "0.45rem", alignItems: "center" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Quick dates:</span>
          {FIRE_DATE_SHORTCUTS.map(s => (
            <button
              key={s.date}
              onClick={() => handleShortcut(s.date)}
              style={{
                padding: "0.25rem 0.65rem",
                borderRadius: "4px",
                border: `1px solid ${selectedDate === s.date ? "rgba(6,182,212,0.5)" : "rgba(255,255,255,0.1)"}`,
                background: selectedDate === s.date ? "rgba(6,182,212,0.15)" : "rgba(255,255,255,0.04)",
                color: selectedDate === s.date ? "#22d3ee" : "var(--text-secondary)",
                fontSize: "0.75rem",
                cursor: "pointer",
                fontWeight: selectedDate === s.date ? 700 : 400
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Wind-free disclaimer */}
      {result && isWindFree && (
        <div style={{
          marginBottom: "1.25rem",
          padding: "0.7rem 1.1rem",
          borderRadius: "8px",
          background: "rgba(245,158,11,0.08)",
          border: "1px solid rgba(245,158,11,0.3)",
          display: "flex", alignItems: "center", gap: "0.6rem",
          fontSize: "0.82rem", color: "#f59e0b"
        }}>
          <Wind size={16} style={{ flexShrink: 0 }} />
          <span>
            <b>Wind-Free Rankings:</b> No daily observed wind data is available for this sample dataset.
            Rankings reflect fire intensity × distance proximity only — not atmospheric transport alignment.
            Results labelled accordingly.
          </span>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-secondary)" }}>
          <RefreshCw size={24} style={{ animation: "spin 1s linear infinite", marginBottom: "0.75rem" }} />
          <div>Computing fire cluster rankings…</div>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="card" style={{
          padding: "1.5rem",
          background: "rgba(239,68,68,0.08)",
          border: "1px solid rgba(239,68,68,0.3)"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", color: "#f87171" }}>
            <AlertCircle size={18} />
            <b>Error:</b> {error}
          </div>
          <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Try selecting a date between Oct 1–Nov 30 2024. The sample dataset covers only this stubble-burning season window.
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && result && clusters.length > 0 && (
        <>
          {/* Summary row */}
          <div className="card-grid" style={{ marginBottom: "1.25rem" }}>
            <div className="card card-kpi">
              <div className="kpi-header">
                <span className="kpi-title">Fire Clusters Ranked</span>
                <div className="kpi-icon-wrap"><Flame size={16} color="var(--accent-amber)" /></div>
              </div>
              <div className="kpi-value" style={{ color: "var(--accent-amber)" }}>{clusters.length}</div>
              <div className="kpi-subtitle">0.5° grid cells with active fires</div>
            </div>
            <div className="card card-kpi">
              <div className="kpi-header">
                <span className="kpi-title">Date Window</span>
                <div className="kpi-icon-wrap"><MapPin size={16} color="var(--accent-cyan)" /></div>
              </div>
              <div className="kpi-value" style={{ color: "var(--accent-cyan)", fontSize: "1.4rem" }}>
                {result.target_date}
              </div>
              <div className="kpi-subtitle">–{result.lookback_days}d lookback</div>
            </div>
            <div className="card card-kpi">
              <div className="kpi-header">
                <span className="kpi-title">Top Cluster FRP</span>
                <div className="kpi-icon-wrap"><TrendingDown size={16} color="#f87171" /></div>
              </div>
              <div className="kpi-value" style={{ color: "#f87171" }}>
                {clusters[0]?.frp_total_mw?.toFixed(0)}
                <span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: 400 }}> MW</span>
              </div>
              <div className="kpi-subtitle">{clusters[0]?.state} — Rank #1</div>
            </div>
            <div className="card card-kpi">
              <div className="kpi-header">
                <span className="kpi-title">Ranking Method</span>
                <div className="kpi-icon-wrap"><Wind size={16} color="var(--text-muted)" /></div>
              </div>
              <div className="kpi-value" style={{ color: "var(--text-secondary)", fontSize: "1.1rem", fontWeight: 700 }}>
                {isWindFree ? "Wind-Free" : "Wind-Aware"}
              </div>
              <div className="kpi-subtitle">FRP × distance-decay weight</div>
            </div>
          </div>

          {/* Main Results Table */}
          <div className="card" style={{ marginBottom: "1.25rem", overflow: "hidden" }}>
            <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, margin: 0 }}>
                Cluster Rankings — {result.target_date}
                {result.lookback_days > 0 ? ` (incl. ${result.lookback_days}d lookback)` : ""}
              </h3>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", background: "rgba(255,255,255,0.05)", padding: "3px 8px", borderRadius: "4px" }}>
                Sample data · VIIRS S-NPP
              </span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th style={{ width: "50px" }}>Rank</th>
                    <th>State</th>
                    <th>Location (centroid)</th>
                    <th>Fires</th>
                    <th>Total FRP (MW)</th>
                    <th>Distance to Delhi</th>
                    <th>Wind-Free Score</th>
                    <th>Score Share</th>
                  </tr>
                </thead>
                <tbody>
                  {clusters.map((c: any) => (
                    <tr key={c.rank}>
                      <td>
                        <span style={{
                          display: "inline-flex", alignItems: "center", justifyContent: "center",
                          width: "28px", height: "28px", borderRadius: "50%",
                          background: `${getRankColor(c.rank)}22`,
                          border: `1px solid ${getRankColor(c.rank)}55`,
                          color: getRankColor(c.rank),
                          fontWeight: 800, fontSize: "0.82rem", fontFamily: "var(--font-mono)"
                        }}>
                          {c.rank}
                        </span>
                      </td>
                      <td>
                        <span
                          className={c.state === "Punjab" ? "badge badge-amber" : "badge badge-purple"}
                          style={{ fontSize: "0.75rem" }}
                        >
                          {c.state}
                        </span>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                        {c.centroid_lat?.toFixed(2)}°N, {c.centroid_lon?.toFixed(2)}°E
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                        {c.n_fires}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--accent-amber)" }}>
                        {c.frp_total_mw?.toFixed(1)}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                        {c.distance_km?.toFixed(0)} km
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                        {c.wind_free_score?.toFixed(1)}
                      </td>
                      <td>{getScoreBar(c.score_share_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Notes / collapsible */}
          {result.notes && result.notes.length > 0 && (
            <div className="card" style={{ marginBottom: "1.25rem", padding: "0.85rem 1.15rem" }}>
              <button
                onClick={() => setShowNotes(v => !v)}
                style={{
                  display: "flex", alignItems: "center", gap: "0.45rem",
                  background: "none", border: "none", color: "var(--text-secondary)",
                  cursor: "pointer", fontSize: "0.82rem", fontWeight: 600, padding: 0
                }}
              >
                {showNotes ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                Ranking Notes ({result.notes.length})
              </button>
              {showNotes && (
                <ul style={{ marginTop: "0.65rem", paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  {result.notes.map((n: string, i: number) => (
                    <li key={i} style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{n}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!loading && !error && result && clusters.length === 0 && (
        <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-secondary)" }}>
          <Flame size={32} color="var(--text-muted)" style={{ marginBottom: "0.75rem" }} />
          <div style={{ fontWeight: 600 }}>No fire clusters found</div>
          <div style={{ fontSize: "0.8rem", marginTop: "0.4rem", color: "var(--text-muted)" }}>
            No valid fire hotspots within the selected date window ({result.target_date}, −{result.lookback_days} days).
            Try a date in Oct–Nov 2024 or increase the lookback window.
          </div>
        </div>
      )}

      {/* Scientific Footer */}
      <div style={{
        padding: "0.75rem 1rem",
        borderRadius: "8px",
        background: "rgba(255,255,255,0.025)",
        border: "1px solid var(--border-subtle)",
        fontSize: "0.75rem",
        color: "var(--text-muted)",
        lineHeight: 1.6
      }}>
        <b style={{ color: "var(--text-dim)" }}>Scientific Disclaimer:</b>{" "}
        Scores are a relative unitless index of transport potential — not a dispersion model output, not in µg/m³.
        The ranking does not simulate smoke chemistry, plume rise, deposition, or travel time.
        Sample fire data covers Oct 1 – Nov 30 2024 (VIIRS S-NPP 375m, NASA LANCE/FIRMS).
        Wind data is unavailable for this sample; results are labelled wind-free accordingly.
      </div>
    </div>
  );
}
