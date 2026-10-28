import React from "react";
import { CheckCircle2, HeartPulse, Building2, Globe, ArrowUpRight, AlertTriangle, ShieldCheck, Award } from "lucide-react";

export default function ResearchInsights() {
  return (
    <div>
      <div className="page-header" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Research Findings & Sustainable Development Goals (SDGs)</h1>
          <p className="page-subtitle">
            Scientific answers to core research questions, methodological caveats, policy implications, and SDG alignment
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <span className="badge badge-cyan">Evaluation Set: 2024 Held-Out (N = 366)</span>
          <span className="badge badge-purple">SDGs 3, 11, 13 Aligned</span>
        </div>
      </div>

      {/* Research Questions Answers */}
      <div className="card" style={{ marginBottom: "1.75rem" }}>
        <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "1rem" }}>
          Core Research Questions — Verified Empirical Conclusions
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* RQ1 */}
          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px", borderLeft: "3px solid var(--accent-cyan)" }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--accent-cyan)", marginBottom: "4px" }}>
              RQ1 — Machine Learning Predictive Feasibility
            </div>
            <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              <b>Finding:</b> Chronological machine learning models reliably predict Delhi's daily citywide PM2.5 concentrations without lookahead leakage. On the complete 366 held-out test days of 2024, our best model (Exp C XGBoost) achieves <b>R² = 0.8472</b>, <b>MAE = 17.86 µg/m³</b>, and <b>RMSE = 26.21 µg/m³</b>, substantially outperforming the naive persistence baseline (R² = 0.6865, MAE = 23.36 µg/m³) and linear ridge regression (R² = 0.8145).
            </p>
          </div>

          {/* RQ2 */}
          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px", borderLeft: "3px solid var(--accent-amber)" }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--accent-amber)", marginBottom: "4px" }}>
              RQ2 — Additional Predictive Value of Agricultural Fire Activity
            </div>
            <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              <b>Finding:</b> Controlled feature ablation demonstrates that satellite active fires in Punjab and Haryana provide measurable incremental predictive information beyond historical pollution and baseline weather. Incorporating raw regional satellite fire counts (Exp B) increases out-of-sample R² from 0.8192 (Baseline Exp A) to <b>0.8355</b> (+0.0163 gain), reducing MAE from 18.92 to 18.20 µg/m³.
            </p>
          </div>

          {/* RQ3 */}
          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px", borderLeft: "3px solid var(--accent-teal)" }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--accent-teal)", marginBottom: "4px" }}>
              RQ3 — Value of Physics-Guided Atmospheric Transport Feature Engineering
            </div>
            <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              <b>Finding:</b> Structuring satellite fire observations with directional wind alignment and distance-decay weighting (Exp C) yields superior predictive skill compared to raw regional fire counts. Exp C achieves <b>R² = 0.8472</b> (+0.0280 over baseline, +0.0117 over raw fires) and reduces MAE to 17.86 µg/m³. Wind-aware transport heuristics selectively amplify biomass burning plumes oriented along the north-westerly advection corridor into Delhi.
            </p>
          </div>

          {/* RQ4 */}
          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px", borderLeft: "3px solid var(--accent-red)" }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--accent-red)", marginBottom: "4px" }}>
              RQ4 — Severe Episode Identification & Early Warning
            </div>
            <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              <b>Finding:</b> On the Study Severe Threshold (PM2.5 ≥ 250 µg/m³, with exactly 21 actual severe days in 2024), Exp C XGBoost delivers an <b>F1-score of 0.6667</b> (Precision = 61.54%, Recall = 72.73%), outperforming the meteorological baseline (F1 = 0.5789) and persistence baseline (F1 = 0.5405). This confirms that fire transport features provide critical discriminative power during acute air quality crises.
            </p>
          </div>

          {/* RQ5 */}
          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px", borderLeft: "3px solid var(--accent-purple)" }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--accent-purple)", marginBottom: "4px" }}>
              RQ5 — TreeSHAP Feature Attribution & Seasonal Dominance
            </div>
            <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              <b>Finding:</b> Verified TreeSHAP arrays show that across the full annual cycle, historical pollution persistence accounts for <b>57.17%</b> of model reliance and meteorology accounts for <b>25.31%</b>, while agricultural fire transport accounts for <b>9.93%</b> (seasonality: 7.59%). However, during the acute post-monsoon harvest window (Oct 15 – Nov 30), fire transport reliance surges to <b>34.8%</b> of the daily model push, confirming its role as an acute episodic driver.
            </p>
          </div>
        </div>
      </div>

      {/* Sustainable Development Goals Alignment */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.25rem", marginBottom: "1.75rem" }}>
        <div className="card" style={{ borderTop: "4px solid #4caf50" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <div style={{ background: "#4caf50", padding: "0.4rem", borderRadius: "6px", color: "#fff" }}>
              <HeartPulse size={20} />
            </div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>SDG 3: Good Health & Well-Being</h3>
          </div>
          <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            <b>Target 3.9:</b> Substantially reduce illnesses and mortality from hazardous air pollution.
            By providing actionable early warning of severe pollution episodes, public health agencies can issue targeted advisories for vulnerable populations (pediatric, geriatric, asthmatic) and schedule elective hospital admissions ahead of peak smog episodes.
          </p>
        </div>

        <div className="card" style={{ borderTop: "4px solid #ff9800" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <div style={{ background: "#ff9800", padding: "0.4rem", borderRadius: "6px", color: "#fff" }}>
              <Building2 size={20} />
            </div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>SDG 11: Sustainable Cities & Communities</h3>
          </div>
          <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            <b>Target 11.6:</b> Reduce the adverse per capita environmental impact of cities.
            Informs decision-makers administering Delhi's Graded Response Action Plan (GRAP), enabling targeted restrictions on diesel generators, industrial operations, and heavy vehicle transit before meteorological trapping exacerbates regional smoke advection.
          </p>
        </div>

        <div className="card" style={{ borderTop: "4px solid #0284c7" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <div style={{ background: "#0284c7", padding: "0.4rem", borderRadius: "6px", color: "#fff" }}>
              <Globe size={20} />
            </div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>SDG 13: Climate Action</h3>
          </div>
          <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            <b>Target 13.1:</b> Strengthen resilience and adaptive capacity to climate-related atmospheric hazards.
            Quantifies the interplay between synoptic weather patterns (boundary layer compression, thermal inversions) and episodic biomass combustion across the Indo-Gangetic Plain.
          </p>
        </div>
      </div>

      {/* Methodological Caveats & Future Scope */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <AlertTriangle size={18} color="var(--accent-amber)" />
          <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Methodological Caveats & Scientific Boundaries</h3>
        </div>
        <ul style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.6, paddingLeft: "1.25rem" }}>
          <li>
            <b>Predictive Association vs Physical Attribution:</b> Machine learning identifies statistical predictive correlations and SHAP mathematical contributions. These must not be interpreted as physical chemical mass fractions (such as isotopic carbon source apportionment or 3D Eulerian CTM mass budgets).
          </li>
          <li>
            <b>Satellite Detection Windows:</b> VIIRS S-NPP provides sun-synchronous afternoon snapshots (approx. 13:30 local time). Cloud cover, heavy smoke obscuration, and nocturnal burning remain unobserved by polar-orbiting optical sensors.
          </li>
          <li>
            <b>Static Cropland Mask:</b> ESA WorldCover 2021 is applied as a static cropland reference across 2018–2025; intra-annual crop rotation and land-use changes are assumed constant.
          </li>
          <li>
            <b>Operational Live Deployment Requirements:</b> Transitioning from historical replay to operational live forecasting requires automated streaming APIs for CPCB telemetry, daily satellite fire feeds, and ECMWF IFS numerical weather forecasts.
          </li>
        </ul>
      </div>
    </div>
  );
}
