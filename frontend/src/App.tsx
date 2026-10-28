import React, { useState } from "react";
import {
  Activity,
  Map as MapIcon,
  BarChart3,
  Cpu,
  HelpCircle,
  AlertTriangle,
  Database,
  Award,
  ChevronRight,
  ExternalLink,
  BookOpen,
  X,
  Wind,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Radio,
  Sliders,
  MapPin,
  Printer
} from "lucide-react";

import { fetchLiveTelemetry } from "./services/api";

import LiveMonitoring from "./pages/LiveMonitoring";
import EnvironmentalOverview from "./pages/EnvironmentalOverview";
import FireTransportMap from "./pages/FireTransportMap";
import SpatialInequality from "./pages/SpatialInequality";
import PollutionAnalysis from "./pages/PollutionAnalysis";
import ModelLaboratory from "./pages/ModelLaboratory";
import AttributionShap from "./pages/AttributionShap";
import EpisodeForecastExplorer from "./pages/EpisodeForecastExplorer";
import PolicySimulator from "./pages/PolicySimulator";
import DataMethodology from "./pages/DataMethodology";
import ResearchInsights from "./pages/ResearchInsights";

interface SubTab {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  description: string;
}

interface NavHub {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  badge?: string;
  badgeType?: "live" | "neutral" | "highlight";
  defaultTab: string;
  subTabs: SubTab[];
}

const NAV_HUBS: NavHub[] = [
  {
    id: "live-hub",
    label: "Live Operations",
    icon: Radio,
    badge: "LIVE",
    badgeType: "live",
    defaultTab: "live",
    subTabs: [
      {
        id: "live",
        label: "Real-Time Telemetry Radar",
        icon: Radio,
        description: "Live Open-Meteo atmospheric stream, boundary layer dynamics, and Delhi CAAQM telemetry."
      },
      {
        id: "overview",
        label: "Citywide Ambient Overview",
        icon: Activity,
        description: "Retrospective and live multi-source environmental snapshot for Delhi NCT."
      }
    ]
  },
  {
    id: "map-hub",
    label: "Fire & Airshed Map",
    icon: MapIcon,
    badge: "GIS",
    badgeType: "neutral",
    defaultTab: "map",
    subTabs: [
      {
        id: "map",
        label: "Punjab-Delhi Transport Corridor",
        icon: MapIcon,
        description: "Interactive satellite fire hotspots (VIIRS 375m), NW advection cone, and distance decay buffers."
      },
      {
        id: "spatial",
        label: "Station Exposure Gradient",
        icon: MapPin,
        description: "Spatial PM2.5 inequality across 40 continuous CAAQM ground monitoring stations in Delhi NCT."
      }
    ]
  },
  {
    id: "policy-hub",
    label: "Policy Lab & AI Forecast",
    icon: Sliders,
    badge: "SIM",
    badgeType: "highlight",
    defaultTab: "simulator",
    subTabs: [
      {
        id: "simulator",
        label: "What-If Policy Lab",
        icon: Sliders,
        description: "Counterfactual farm fire abatement sliders (Punjab/Haryana 0–100%) and averted health outcomes."
      },
      {
        id: "forecast",
        label: "Episode Forecast Explorer",
        icon: AlertTriangle,
        description: "Multi-model predictions with conformal uncertainty bounds (±26.2 µg/m³) and severe threshold alarms."
      }
    ]
  },
  {
    id: "attribution-hub",
    label: "Source Attribution",
    icon: HelpCircle,
    defaultTab: "shap",
    subTabs: [
      {
        id: "shap",
        label: "TreeSHAP Attribution Breakdown",
        icon: HelpCircle,
        description: "Additive mathematical attribution: biomass smoke push vs urban baseline floor vs inversion trap."
      },
      {
        id: "pollution",
        label: "Multi-Year Pollution Trends",
        icon: BarChart3,
        description: "Longitudinal PM2.5 dynamics and seasonal harvest burning spikes across 2018–2025."
      }
    ]
  },
  {
    id: "science-hub",
    label: "Science & Methodology",
    icon: Database,
    defaultTab: "models",
    subTabs: [
      {
        id: "models",
        label: "Model Benchmark Lab",
        icon: Cpu,
        description: "Rigorous chronological test evaluation (Exp C XGBoost achieves R² = 0.8472, MAE = 17.86 µg/m³)."
      },
      {
        id: "data",
        label: "Data Pipelines & Sources",
        icon: Database,
        description: "Continuous integration of 40 CPCB CAAQM stations, NASA FIRMS VIIRS, and ECMWF ERA5."
      },
      {
        id: "insights",
        label: "Research Insights & SDGs",
        icon: Award,
        description: "Academic capstone findings, statutory CAQM policy synthesis, and UN Sustainable Development Goals."
      }
    ]
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState<string>("live");
  const [showBriefModal, setShowBriefModal] = useState<boolean>(false);
  const [showLiveModal, setShowLiveModal] = useState<boolean>(false);
  const [liveData, setLiveData] = useState<any>(null);
  const [liveLoading, setLiveLoading] = useState<boolean>(false);

  const openLiveTelemetry = () => {
    setShowLiveModal(true);
    setLiveLoading(true);
    fetchLiveTelemetry()
      .then((data) => {
        setLiveData(data);
      })
      .catch((err) => {
        console.error("fetchLiveTelemetry error:", err);
      })
      .finally(() => {
        setLiveLoading(false);
      });
  };

  // Find active hub and active subtab
  const activeHub = NAV_HUBS.find((h) => h.subTabs.some((s) => s.id === activeTab)) || NAV_HUBS[0];
  const activeSubTab = activeHub.subTabs.find((s) => s.id === activeTab) || activeHub.subTabs[0];

  const handleSelectHub = (hub: NavHub) => {
    // If already in this hub, do nothing or keep current subtab
    const isAlreadyInHub = hub.subTabs.some((s) => s.id === activeTab);
    if (!isAlreadyInHub) {
      setActiveTab(hub.defaultTab);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        {/* Brand Header */}
        <div className="brand">
          <div className="brand-icon-wrapper">
            <Wind size={22} color="#040812" strokeWidth={2.5} />
          </div>
          <div className="brand-text">
            <h1>Tracing the Smoke</h1>
            <p>Atmospheric AI & Attribution</p>
          </div>
        </div>

        {/* 5 Core Workspaces */}
        <div className="nav-section">
          <div className="nav-section-title">Workspaces</div>
          <ul className="nav-list">
            {NAV_HUBS.map((hub) => {
              const Icon = hub.icon;
              const isHubActive = hub.id === activeHub.id;
              return (
                <li
                  key={hub.id}
                  className={`nav-item ${isHubActive ? "active" : ""}`}
                  onClick={() => handleSelectHub(hub)}
                >
                  <Icon size={18} />
                  <span style={{ flex: 1 }}>{hub.label}</span>
                  {hub.badge && (
                    <span
                      style={{
                        fontSize: "0.68rem",
                        padding: "1px 6px",
                        borderRadius: "4px",
                        background:
                          hub.badgeType === "live"
                            ? "rgba(16,185,129,0.18)"
                            : isHubActive
                            ? "rgba(6,182,212,0.25)"
                            : "rgba(255,255,255,0.06)",
                        color:
                          hub.badgeType === "live"
                            ? "#34d399"
                            : isHubActive
                            ? "var(--accent-cyan)"
                            : "var(--text-muted)",
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600
                      }}
                    >
                      {hub.badge}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>

        {/* Quick Study Metadata */}
        <div style={{ marginTop: "1.5rem", padding: "0.75rem", background: "rgba(255,255,255,0.03)", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.5px" }}>
            Benchmark Model
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--accent-cyan)", fontWeight: 700, marginTop: "2px" }}>
            Exp C XGBoost (Physics)
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "4px", lineHeight: 1.4 }}>
            R² = <b>0.8472</b> • MAE = 17.86 µg/m³<br />
            Held-out 2024 test split (366 days)
          </div>
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-footer-badge">
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981" }} />
            <span>Operational • Delhi NCT</span>
          </div>
          <div style={{ color: "var(--text-dim)", lineHeight: 1.4, fontSize: "0.7rem" }}>
            40 CPCB Stations • VIIRS S-NPP • ERA5
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="content-wrapper">
        {/* Top App Header */}
        <header className="app-header">
          <div className="header-left">
            <div className="header-breadcrumbs">
              <span style={{ color: "var(--text-muted)" }}>Tracing the Smoke</span>
              <ChevronRight size={14} />
              <span style={{ color: "var(--text-secondary)" }}>{activeHub.label}</span>
              <ChevronRight size={14} />
              <span className="current">{activeSubTab.label}</span>
            </div>
          </div>

          <div className="header-right">
            {/* Live Operational Status */}
            <div
              className="pulse-indicator emerald"
              style={{ cursor: "pointer" }}
              onClick={openLiveTelemetry}
              title="Click to inspect live atmospheric telemetry feed"
            >
              <span className="pulse-dot" />
              <span>40 CAAQM Stations Live</span>
            </div>

            {/* Executive Intelligence Dossier Trigger */}
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => setShowBriefModal(true)}
              style={{
                gap: "0.4rem",
                background: "rgba(6, 182, 212, 0.1)",
                borderColor: "rgba(6, 182, 212, 0.3)",
                color: "#22d3ee"
              }}
            >
              <FileText size={14} />
              <span>Executive Dossier</span>
            </button>

            {/* Backend Swagger API Link */}
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="btn btn-outline btn-sm"
              style={{ gap: "0.35rem", textDecoration: "none" }}
              title="Interactive OpenAPI / Swagger Documentation"
            >
              <ExternalLink size={14} />
              <span>API</span>
            </a>
          </div>
        </header>

        {/* Main Content Router */}
        <main className="main-content">
          {/* Segmented Sub-Navigation Switcher */}
          <div className="subnav-bar">
            <div className="segmented-control">
              {activeHub.subTabs.map((sub) => {
                const SubIcon = sub.icon;
                const isSelected = activeTab === sub.id;
                return (
                  <button
                    key={sub.id}
                    type="button"
                    className={`segmented-tab ${isSelected ? "active" : ""}`}
                    onClick={() => setActiveTab(sub.id)}
                  >
                    <SubIcon size={14} />
                    <span>{sub.label}</span>
                  </button>
                );
              })}
            </div>
            <div className="subnav-desc">
              {activeSubTab.description}
            </div>
          </div>

          {/* Active Workspace View */}
          {activeTab === "live" && <LiveMonitoring />}
          {activeTab === "overview" && <EnvironmentalOverview />}
          {activeTab === "map" && <FireTransportMap />}
          {activeTab === "spatial" && <SpatialInequality />}
          {activeTab === "pollution" && <PollutionAnalysis />}
          {activeTab === "models" && <ModelLaboratory />}
          {activeTab === "shap" && <AttributionShap />}
          {activeTab === "forecast" && <EpisodeForecastExplorer />}
          {activeTab === "simulator" && <PolicySimulator />}
          {activeTab === "data" && <DataMethodology />}
          {activeTab === "insights" && <ResearchInsights />}
        </main>
      </div>

      {/* Executive Intelligence Dossier Modal */}
      {showBriefModal && (
        <div className="modal-overlay" onClick={() => setShowBriefModal(false)}>
          <div className="modal-card" style={{ maxWidth: "720px", padding: "1.75rem" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "1rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <ShieldCheck size={20} color="var(--accent-cyan)" />
                  <h3 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                    Executive Intelligence Dossier & Policy Briefing
                  </h3>
                </div>
                <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                  Commission for Air Quality Management (CAQM) & CPCB Atmospheric Attribution Standard
                </p>
              </div>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="btn btn-outline btn-sm"
                  style={{ gap: "0.35rem", color: "var(--accent-teal)" }}
                  title="Print or Save as PDF"
                >
                  <Printer size={14} />
                  <span>Print Dossier</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowBriefModal(false)}
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    border: "none",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    color: "var(--text-secondary)",
                    cursor: "pointer"
                  }}
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "1.1rem", fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              {/* Highlight Finding */}
              <div style={{ background: "rgba(6,182,212,0.08)", border: "1px solid rgba(6,182,212,0.25)", borderRadius: "8px", padding: "1rem" }}>
                <b style={{ color: "var(--accent-cyan)", fontSize: "0.92rem" }}>
                  Verified Empirical Finding (Held-Out 2024 Test Split, N = 366 Days):
                </b>
                <div style={{ marginTop: "6px" }}>
                  Physics-guided atmospheric transport features (Exp C: distance-decay + 315° NW advection alignment) improve out-of-sample PM2.5 prediction skill to <b>R² = 0.8472</b> and <b>MAE = 17.86 µg/m³</b>, substantially surpassing raw regional fires (Exp B: R² = 0.8355), baseline weather (Exp A: R² = 0.8192), and persistence (R² = 0.6865).
                </div>
              </div>

              {/* Data Sources Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "6px" }}>
                  <div style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.82rem" }}>CPCB Ground Telemetry</div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    40 eligible CAAQM stations across Delhi NCT; mean reporting of 34 stations/day (2018–2025).
                  </div>
                </div>
                <div style={{ background: "var(--bg-secondary)", padding: "0.75rem", borderRadius: "6px" }}>
                  <div style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.82rem" }}>NASA FIRMS Satellite Detections</div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    VIIRS S-NPP 375m high-resolution active fires confirmed with ESA WorldCover cropland mask.
                  </div>
                </div>
              </div>

              {/* Attribution Decomposition */}
              <div>
                <h4 style={{ color: "var(--text-primary)", fontWeight: 700, marginBottom: "6px" }}>
                  TreeSHAP Numerical Attribution Breakdown
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.5rem", textAlign: "center" }}>
                  <div style={{ background: "var(--bg-secondary)", padding: "0.5rem", borderRadius: "6px" }}>
                    <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--accent-amber)" }}>57.2%</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Urban Floor Persistence</div>
                  </div>
                  <div style={{ background: "var(--bg-secondary)", padding: "0.5rem", borderRadius: "6px" }}>
                    <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--accent-teal)" }}>25.3%</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Dispersion & Inversion</div>
                  </div>
                  <div style={{ background: "var(--bg-secondary)", padding: "0.5rem", borderRadius: "6px" }}>
                    <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#f87171" }}>34.8%</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Peak Harvest Smoke Push</div>
                  </div>
                  <div style={{ background: "var(--bg-secondary)", padding: "0.5rem", borderRadius: "6px" }}>
                    <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--accent-purple)" }}>7.6%</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Synoptic Seasonality</div>
                  </div>
                </div>
              </div>

              {/* Statutory GRAP Protocol Table */}
              <div>
                <h4 style={{ color: "var(--text-primary)", fontWeight: 700, marginBottom: "6px" }}>
                  Statutory CAQM GRAP Trigger Matrix
                </h4>
                <table className="data-table" style={{ width: "100%", fontSize: "0.78rem" }}>
                  <thead>
                    <tr>
                      <th>Threshold</th>
                      <th>GRAP Stage</th>
                      <th>Key Mandated Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td style={{ fontFamily: "var(--font-mono)" }}>PM2.5 &gt; 380 µg/m³</td>
                      <td><span className="badge badge-severe">Stage IV (Severe+)</span></td>
                      <td>Ban non-BS VI diesel commercial trucks; shift primary schools to online classes.</td>
                    </tr>
                    <tr>
                      <td style={{ fontFamily: "var(--font-mono)" }}>PM2.5 250–380 µg/m³</td>
                      <td><span className="badge badge-caution">Stage III (Severe)</span></td>
                      <td>Ban BS-III petrol & BS-IV diesel cars; halt non-essential construction & demolition.</td>
                    </tr>
                    <tr>
                      <td style={{ fontFamily: "var(--font-mono)" }}>PM2.5 120–250 µg/m³</td>
                      <td><span className="badge badge-cyan">Stage II (Very Poor)</span></td>
                      <td>Enforce mechanised road sweeping; augment public transport frequency; restrict diesel gensets.</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Modal Footer */}
              <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "0.85rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  Verified Machine Learning System • UN SDGs 3, 11, and 13
                </span>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => setShowBriefModal(false)}
                >
                  Close Dossier
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Live Operational Telemetry Modal */}
      {showLiveModal && (
        <div className="modal-overlay" onClick={() => setShowLiveModal(false)}>
          <div className="modal-card" style={{ maxWidth: "720px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
                <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "rgba(16, 185, 129, 0.15)", border: "1px solid rgba(16, 185, 129, 0.3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Radio size={20} color="#10b981" />
                </div>
                <div>
                  <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    Real-Time Atmospheric Telemetry Feed
                  </h3>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                    Live Open-Meteo NWP Stream • Advection Alignment • CPCB Delhi CAAQM Grid
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowLiveModal(false)}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "none",
                  borderRadius: "6px",
                  padding: "4px 8px",
                  color: "var(--text-secondary)",
                  cursor: "pointer"
                }}
              >
                <X size={16} />
              </button>
            </div>

            {liveLoading ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-secondary)" }}>
                Connecting to live weather telemetry stream...
              </div>
            ) : liveData ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.15rem" }}>
                {/* Status banner */}
                <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "8px", padding: "0.75rem 1rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.82rem", color: "#6ee7b7" }}>
                    <CheckCircle2 size={16} color="#10b981" />
                    <span><b>Live Stream Online:</b> Synced at {liveData.query_time}</span>
                  </div>
                  <span className="badge badge-good" style={{ fontSize: "0.7rem" }}>
                    {liveData.weather?.status}
                  </span>
                </div>

                {/* 4 Telemetry Metrics */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.75rem" }}>
                  <div className="card" style={{ padding: "0.85rem" }}>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Current Temp</div>
                    <div style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--accent-cyan)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                      {liveData.weather?.temperature_c}°C
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                      Humidity: {liveData.weather?.relative_humidity_pct}%
                    </div>
                  </div>

                  <div className="card" style={{ padding: "0.85rem" }}>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>10m Wind Vector</div>
                    <div style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--accent-teal)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                      {liveData.weather?.wind_speed_ms} <span style={{ fontSize: "0.8rem", fontWeight: 400 }}>m/s</span>
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                      Bearing: {liveData.weather?.wind_direction_deg}°
                    </div>
                  </div>

                  <div className="card" style={{ padding: "0.85rem" }}>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Boundary Layer (BLH)</div>
                    <div style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--accent-purple)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                      {liveData.weather?.boundary_layer_height_m} <span style={{ fontSize: "0.8rem", fontWeight: 400 }}>m</span>
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                      Ventilation: {liveData.weather?.ventilation_index} m²/s
                    </div>
                  </div>

                  <div className="card" style={{ padding: "0.85rem" }}>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Advection Alignment</div>
                    <div style={{ fontSize: "1.35rem", fontWeight: 700, color: liveData.transport_analysis?.is_upwind_corridor_active ? "var(--accent-amber)" : "var(--accent-emerald)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                      {(liveData.transport_analysis?.advection_alignment_coefficient * 100).toFixed(0)}%
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                      {liveData.transport_analysis?.corridor_orientation}
                    </div>
                  </div>
                </div>

                {/* Stagnation & Risk evaluation */}
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                      Live Smoke Transport Risk Assessment:
                    </span>
                    <span className={`badge ${liveData.transport_analysis?.smoke_transport_risk === "HIGH" ? "badge-severe" : liveData.transport_analysis?.smoke_transport_risk === "MODERATE" ? "badge-caution" : "badge-good"}`}>
                      {liveData.transport_analysis?.smoke_transport_risk} ADVECTION RISK
                    </span>
                  </div>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {liveData.transport_analysis?.is_upwind_corridor_active
                      ? "Current wind direction is aligned with the north-westerly Punjab–Haryana corridor. Any active biomass burning plumes will advect directly towards the Delhi NCR receptor."
                      : "Current wind vectors are crosswind or calm, minimizing direct horizontal advection from the north-west corridor."}
                    {" "}
                    {liveData.transport_analysis?.inversion_trapping_active && "A shallow planetary boundary layer (< 300m) is active, suppressing vertical dispersion and promoting surface pollutant accumulation."}
                  </p>
                </div>

                {/* Operational Roadmap note */}
                <div style={{ fontSize: "0.76rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-color)", paddingTop: "0.75rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>Source: {liveData.operational_manifest?.telemetry_stream}</span>
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={() => openLiveTelemetry()}
                  >
                    Refresh Telemetry
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
