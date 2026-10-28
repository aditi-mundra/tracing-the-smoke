import React, { useEffect, useState } from "react";
import { Database, BookOpen, Layers, Check, Shield, GitBranch, AlertTriangle } from "lucide-react";
import { fetchStations, fetchMetadata } from "../services/api";

export default function DataMethodology() {
  const [stations, setStations] = useState<any[]>([]);
  const [metadata, setMetadata] = useState<any>(null);

  useEffect(() => {
    fetchStations().then(setStations).catch(console.error);
    fetchMetadata().then(setMetadata).catch(console.error);
  }, []);

  return (
    <div>
      <div className="page-header" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Data Provenance & Scientific Methodology</h1>
          <p className="page-subtitle">
            Rigorous documentation of authentic multi-source environmental datasets, mathematical transport formulations, and validation protocols
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <span className="badge badge-cyan">Chronological Split: 2018–2022 / 2023 / 2024</span>
          <span className="badge badge-purple">40 Eligible Delhi NCT Stations</span>
        </div>
      </div>

      {/* Dataset Provenance Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem", marginBottom: "1.75rem" }}>
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <Database size={18} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>1. Delhi CPCB PM2.5 Network</h3>
          </div>
          <ul style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6, paddingLeft: "1.2rem" }}>
            <li><b>Source:</b> CPCB Continuous Ambient Air Quality Monitoring (CAAQM) via XKDR Forum Database.</li>
            <li><b>Network Scale:</b> <b>40 eligible CAAQM stations</b> located strictly within Delhi NCT (out of 53 discovered regional NCR records).</li>
            <li><b>Daily Reporting:</b> 10 to 38 active stations daily (mean: 33.85 ~ 34 stations, median: 35 stations).</li>
            <li><b>Temporal Scope:</b> 2018–2025 continuous multi-year series (2,922 calendar days).</li>
            <li><b>Valid Daily Observations:</b> Exactly <b>2,709 valid target days</b> (91,694 station-day observations; partial 2025 coverage through June).</li>
            <li><b>Target Summary:</b> Historical mean PM2.5 = <b>99.98 µg/m³</b>; exactly <b>157 study severe days</b> (≥ 250 µg/m³); peak = 589.72 µg/m³ on Nov 18, 2024.</li>
          </ul>
        </div>

        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <Layers size={18} color="var(--accent-amber)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>2. NASA FIRMS VIIRS Active Fires</h3>
          </div>
          <ul style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6, paddingLeft: "1.2rem" }}>
            <li><b>Source:</b> NASA LANCE / FIRMS VIIRS S-NPP (375 m I-band resolution).</li>
            <li><b>Geographic Filter:</b> Administrative state polygon boundaries for Punjab and Haryana.</li>
            <li><b>Dataset B1:</b> 605,537 active-fire detections within regional state polygons.</li>
            <li><b>Dataset B2:</b> 565,728 satellite active-fire detections intersecting <b>ESA WorldCover 10m cropland pixels</b>.</li>
            <li><b>Static Land-Cover Reference:</b> The 2021 ESA WorldCover classification is applied as a consistent static cropland reference across the multi-year study.</li>
            <li><b>Timezone Alignment:</b> UTC acquisition timestamps converted to Indian Standard Time (IST, UTC+5:30).</li>
          </ul>
        </div>

        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <BookOpen size={18} color="var(--accent-teal)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>3. ECMWF ERA5 Meteorology</h3>
          </div>
          <ul style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6, paddingLeft: "1.2rem" }}>
            <li><b>Source:</b> Copernicus ECMWF ERA5 Atmospheric Reanalysis Single Levels.</li>
            <li><b>Surface Variables:</b> 2m Temperature (K/°C), 2m Dewpoint (K/°C), 10m U/V Wind components (m/s), Surface Pressure (hPa).</li>
            <li><b>Core Weather Completeness:</b> 2,922 days (100% complete core surface weather).</li>
            <li><b>Boundary Layer Height (BLH):</b> 2,739 days complete; <b>183 incomplete days</b> (181 missing + 2 partial in Jan–Jul 2024).</li>
            <li><b>BLH Missingness Treatment:</b> Documented and handled via training-only fitted estimators for Exp C full-year continuity; pure observed subsets evaluated in sensitivity tests.</li>
            <li><b>Derived Metrics:</b> Ventilation Index = Wind Speed × BLH (m²/s); circular wind direction.</li>
          </ul>
        </div>
      </div>

      {/* Chronological Validation Split */}
      <div className="card" style={{ marginBottom: "1.75rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <GitBranch size={18} color="var(--accent-purple)" />
          <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>
            Chronological Split & Data Leakage Prevention Protocol
          </h3>
        </div>
        <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "1rem" }}>
          To prevent temporal data leakage, all models are trained, tuned, and evaluated strictly chronologically.
          Preprocessors (imputers, scalers) are fitted <b>exclusively on training data</b> and applied downstream without refitting.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem" }}>
          <div style={{ background: "var(--bg-secondary)", padding: "0.85rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Training Partition</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--accent-cyan)" }}>2018 – 2022</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              1,768 valid days (historical training base)
            </div>
          </div>
          <div style={{ background: "var(--bg-secondary)", padding: "0.85rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Validation Partition</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--accent-amber)" }}>2023 (Full Year)</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              365 days (hyperparameter tuning & feature selection)
            </div>
          </div>
          <div style={{ background: "var(--bg-secondary)", padding: "0.85rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Held-Out Test Partition</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--accent-green)" }}>2024 (Full Leap Year)</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              366 days (unseen chronological evaluation)
            </div>
          </div>
          <div style={{ background: "var(--bg-secondary)", padding: "0.85rem", borderRadius: "8px" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Post-Study Archive</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-muted)" }}>2025 (Partial)</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              210 days (monitoring archive through June 2025)
            </div>
          </div>
        </div>
      </div>

      {/* Mathematical Formulations Card */}
      <div className="card" style={{ marginBottom: "1.75rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          Feature-Engineering Transport Formulations (Empirical Heuristics vs Physical Dispersion)
        </h3>
        <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
          The engineered features represent <b>physics-guided machine-learning feature engineering heuristics</b> designed to structure satellite fire observations for tabular gradient boosting, not physical numerical chemical transport simulations (such as CMAQ or WRF-Chem).
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px" }}>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--accent-cyan)", marginBottom: "4px" }}>
              Great-Circle Haversine Distance
            </div>
            <code style={{ fontSize: "0.8rem", color: "var(--text-primary)" }}>
              d = 2R · arcsin(√(sin²(Δφ/2) + cos φ₁ cos φ₂ sin²(Δλ/2)))
            </code>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "6px" }}>
              Calculates exact spherical distance in kilometers between individual satellite fire coordinates and the Delhi receptor centroid (28.6139°N, 77.2090°E).
            </p>
          </div>

          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px" }}>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--accent-amber)", marginBottom: "4px" }}>
              Upwind Transport Alignment
            </div>
            <code style={{ fontSize: "0.8rem", color: "var(--text-primary)" }}>
              Alignment = max(0, cos(θ_bearing - θ_wind_transport))
            </code>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "6px" }}>
              Accounts for meteorological convention (wind direction FROM which wind blows), projecting directional alignment of smoke advecting into Delhi.
            </p>
          </div>

          <div style={{ background: "var(--bg-secondary)", padding: "1rem", borderRadius: "8px" }}>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--accent-teal)", marginBottom: "4px" }}>
              Distance Decay Weighting Factor
            </div>
            <code style={{ fontSize: "0.8rem", color: "var(--text-primary)" }}>
              w(d) = 1 / (1 + (d / 150 km)^1.5)
            </code>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "6px" }}>
              Empirical weighting function capturing plume dilution and dry deposition across the regional transport corridor.
            </p>
          </div>
        </div>
      </div>

      {/* Monitoring Station Directory */}
      <div className="card">
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          Delhi NCT Monitoring Station Directory ({stations.length} Eligible Stations Displayed)
        </h3>
        <div className="table-container" style={{ maxHeight: "320px", overflowY: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Station ID</th>
                <th>Station Name</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {stations.slice(0, 40).map((st: any, idx: number) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600, color: "var(--accent-cyan)" }}>{st.station_id}</td>
                  <td>{st.station_name}</td>
                  <td>{st.latitude?.toFixed(4)}</td>
                  <td>{st.longitude?.toFixed(4)}</td>
                  <td>
                    <span className="badge badge-good">Eligible CAAQM Station</span>
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
