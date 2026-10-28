import React, { useState, useEffect, useRef } from "react";
import L from "leaflet";
import ReactECharts from "echarts-for-react";
import {
  Compass,
  MapPin,
  TrendingUp,
  ShieldAlert,
  Layers,
  ArrowRight,
  Info,
  Activity,
  AlertTriangle,
  Building,
  CheckCircle2
} from "lucide-react";
import { fetchSpatialStations } from "../services/api";
import CalendarDateSelector, { DEFAULT_SHORTCUTS } from "../components/CalendarDateSelector";

const DELHI_CENTER: [number, number] = [28.65, 77.15];
const NW_ENTRY_POINT: [number, number] = [28.8526, 77.0924];

export default function SpatialInequality() {
  const [selectedDate, setSelectedDate] = useState<string>("2024-11-18");
  const [spatialData, setSpatialData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedDistrict, setSelectedDistrict] = useState<string>("All");

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchSpatialStations(selectedDate)
      .then((data) => {
        setSpatialData(data);
      })
      .catch((err) => {
        console.error("fetchSpatialStations error:", err);
      })
      .finally(() => setLoading(false));
  }, [selectedDate]);

  // Leaflet Map Init
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if ((mapContainerRef.current as any)._leaflet_id) {
      (mapContainerRef.current as any)._leaflet_id = null;
    }

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const map = L.map(mapContainerRef.current, {
      zoomControl: true,
      scrollWheelZoom: true
    }).setView(DELHI_CENTER, 10);

    const osmTile = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
      crossOrigin: true
    });
    const cartoTile = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19
    });
    osmTile.addTo(map);
    osmTile.on("tileerror", () => {
      if (map.hasLayer(osmTile)) { map.removeLayer(osmTile); cartoTile.addTo(map); }
    });

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    const t = setTimeout(() => map.invalidateSize(), 200);

    return () => {
      clearTimeout(t);
      map.remove();
      mapInstanceRef.current = null;
      layerGroupRef.current = null;
    };
  }, []);

  // Map Layer Updates
  useEffect(() => {
    const layerGroup = layerGroupRef.current;
    const map = mapInstanceRef.current;
    if (!layerGroup || !map || !spatialData) return;

    map.invalidateSize();
    layerGroup.clearLayers();

    // 1. Singhu Border NW Inflow Entry Point Marker
    const nwBeacon = L.divIcon({
      className: "custom-nw-beacon",
      html: `
        <div style="position: relative; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; width: 24px; height: 24px; border-radius: 50%; background: rgba(239, 68, 68, 0.4); animation: pulse-red 2s infinite;"></div>
          <div style="position: relative; width: 12px; height: 12px; border-radius: 50%; background: #ef4444; border: 2px solid #ffffff;"></div>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const nwMarker = L.marker(NW_ENTRY_POINT, { icon: nwBeacon });
    nwMarker.bindTooltip("Singhu / Narela Smoke Entry Corridor Gateway (From Punjab & Haryana)", { permanent: false });
    layerGroup.addLayer(nwMarker);

    // 2. NW Inflow Arrow Vector into Delhi
    const flowVector = L.polyline([NW_ENTRY_POINT, [28.6139, 77.2090]], {
      color: "#f59e0b",
      weight: 2,
      dashArray: "6, 8",
      opacity: 0.65
    });
    flowVector.bindTooltip("Prevailing 315° NW Advection Gradient Path", { sticky: true });
    layerGroup.addLayer(flowVector);

    // 3. Render 40 CAAQM Stations
    const stationsList = spatialData.stations || [];
    stationsList.forEach((st: any) => {
      if (selectedDistrict !== "All" && st.district !== selectedDistrict) {
        return;
      }

      const isEntry = st.is_corridor_entry;
      const marker = L.circleMarker([st.latitude, st.longitude], {
        radius: isEntry ? 7.5 : 5.5,
        color: isEntry ? "#ffffff" : st.color,
        fillColor: st.color,
        fillOpacity: 0.9,
        weight: isEntry ? 2 : 1
      });

      marker.bindPopup(`
        <div style="font-family: inherit; font-size: 0.82rem; color: #0f172a; line-height: 1.45; padding: 4px;">
          <b style="font-size: 0.9rem; color: ${st.color};">${st.station_name}</b><br />
          District: <b>${st.district}</b><br />
          PM2.5 on ${selectedDate}: <b style="font-size: 1rem; color: ${st.color};">${st.pm25} µg/m³</b><br />
          Category: <b>${st.category}</b><br />
          Distance from NW Border: <b>${st.distance_to_nw_border_km} km</b><br />
          ${isEntry ? '<span style="color: #b91c1c; font-weight: 700;">Direct Entry Corridor Site</span>' : ""}
        </div>
      `);

      marker.bindTooltip(`${st.station_name.split(",")[0]}: ${st.pm25} µg/m³`, {
        direction: "top",
        className: "leaflet-tooltip-dark"
      });

      layerGroup.addLayer(marker);
    });
  }, [spatialData, selectedDate, selectedDistrict]);

  const stations = spatialData?.stations || [];
  const districts = ["All", ...Array.from(new Set(stations.map((s: any) => s.district))).sort()];

  // Ranked horizontal bar chart option
  const filteredStations = selectedDistrict === "All" ? stations : stations.filter((s: any) => s.district === selectedDistrict);
  const chartData = [...filteredStations].slice(0, 20).reverse();

  const rankChartOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#1e293b",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#f8fafc" },
      formatter: (params: any[]) => {
        const item = params[0];
        return `<b>${item.name}</b><br/>PM2.5: <b>${item.value} µg/m³</b>`;
      }
    },
    grid: { left: "10", right: "40", top: "20", bottom: "10", containLabel: true },
    xAxis: {
      type: "value",
      name: "PM2.5 (µg/m³)",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      axisLabel: { color: "#94a3b8" }
    },
    yAxis: {
      type: "category",
      data: chartData.map((s: any) => s.station_name.split(",")[0]),
      axisLabel: { color: "#cbd5e1", fontSize: 11 }
    },
    series: [
      {
        type: "bar",
        data: chartData.map((s: any) => ({
          value: s.pm25,
          itemStyle: { color: s.color }
        })),
        label: {
          show: true,
          position: "right",
          color: "#94a3b8",
          fontSize: 10,
          formatter: "{c} µg"
        }
      }
    ]
  };

  // District Aggregations
  const districtAggMap: Record<string, { count: number; sum: number; max: number; maxName: string }> = {};
  stations.forEach((st: any) => {
    const d = st.district;
    if (!districtAggMap[d]) {
      districtAggMap[d] = { count: 0, sum: 0, max: 0, maxName: "" };
    }
    districtAggMap[d].count += 1;
    districtAggMap[d].sum += st.pm25;
    if (st.pm25 > districtAggMap[d].max) {
      districtAggMap[d].max = st.pm25;
      districtAggMap[d].maxName = st.station_name.split(",")[0];
    }
  });

  const districtRows = Object.entries(districtAggMap)
    .map(([dist, v]) => ({
      district: dist,
      count: v.count,
      mean: Math.round(v.sum / v.count),
      max: v.max,
      maxName: v.maxName
    }))
    .sort((a, b) => b.mean - a.mean);

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Intra-Urban Smog Inequality & Spatial Station Network</h1>
          <p className="page-subtitle">
            Station-level air pollution exposure distribution across Delhi NCT's 40 CAAQM stations. Analyzes the spatial smoke gradient entering from Punjab & Haryana.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <span className="badge badge-cyan">40 Active CAAQM Stations</span>
          <span className="badge badge-purple">Spatial Advection Gradient</span>
          <span className="badge badge-caution">Singhu / Narela Corridor Gateway</span>
        </div>
      </div>

      {/* Date Picker */}
      <div className="card" style={{ marginBottom: "1.25rem", padding: "0.85rem 1.15rem" }}>
        <CalendarDateSelector
          value={selectedDate}
          onChange={setSelectedDate}
          minDate="2018-01-01"
          maxDate="2025-12-31"
          label="Observation Date"
          helperText="Select any date to inspect the station-level spatial gradient across Delhi NCT."
          shortcuts={DEFAULT_SHORTCUTS}
        />
      </div>

      {/* KPI Cards Bar */}
      <div className="card-grid" style={{ marginBottom: "1.25rem" }}>
        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Citywide Average PM2.5</span>
            <div className="kpi-icon-wrap">
              <Activity size={16} color="var(--accent-cyan)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-cyan)" }}>
            {spatialData?.citywide_mean_pm25 ?? "—"}{" "}
            <span style={{ fontSize: "1rem", color: "var(--text-muted)" }}>µg/m³</span>
          </div>
          <div className="kpi-subtitle">Mean of active reporting stations</div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">NW Entry Corridor Mean</span>
            <div className="kpi-icon-wrap">
              <Compass size={16} color="#ef4444" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "#f87171" }}>
            {spatialData?.nw_entry_corridor_mean_pm25 ?? "—"}{" "}
            <span style={{ fontSize: "1rem", color: "var(--text-muted)" }}>µg/m³</span>
          </div>
          <div className="kpi-subtitle">Narela, Bawana, Jahangirpuri, Rohini</div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">South Delhi Downwind Mean</span>
            <div className="kpi-icon-wrap">
              <TrendingUp size={16} color="var(--accent-emerald)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-emerald)" }}>
            {spatialData?.south_delhi_mean_pm25 ?? "—"}{" "}
            <span style={{ fontSize: "1rem", color: "var(--text-muted)" }}>µg/m³</span>
          </div>
          <div className="kpi-subtitle">Lodhi Rd, Mandir Marg, Aurobindo Marg</div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Corridor Gradient Ratio</span>
            <div className="kpi-icon-wrap">
              <TrendingUp size={16} color="var(--accent-purple)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-purple)" }}>
            {spatialData?.spatial_gradient_ratio ?? "1.00"}x
          </div>
          <div className="kpi-subtitle">NW entry exposure vs South Delhi</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="card"
        style={{
          marginBottom: "1.25rem",
          padding: "0.75rem 1.15rem",
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          flexWrap: "wrap"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
          <Building size={16} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-secondary)" }}>District Filter:</span>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            style={{
              background: "var(--bg-secondary)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-color)",
              padding: "0.35rem 0.65rem",
              borderRadius: "6px",
              fontSize: "0.82rem"
            }}
          >
            {districts.map((d: any) => (
              <option key={d} value={d}>
                {d === "All" ? "All Districts (40 Stations)" : d}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", marginLeft: "auto", fontSize: "0.75rem" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#b91c1c" }} />
            Severe+ (&gt; 380)
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444" }} />
            Severe (250–380)
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f97316" }} />
            Very Poor (120–250)
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#eab308" }} />
            Poor (60–120)
          </span>
        </div>
      </div>

      {/* Main Grid: Map & Ranked Bar Chart */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
          gap: "1.25rem",
          marginBottom: "1.25rem"
        }}
      >
        {/* Leaflet Map Box */}
        <div className="card" style={{ padding: "0.85rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.65rem" }}>
            <h4 style={{ fontSize: "0.92rem", fontWeight: 700, margin: 0 }}>
              Spatial Station Exposure Map
            </h4>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {filteredStations.length} stations displayed
            </span>
          </div>
          <div ref={mapContainerRef} style={{ height: "460px", width: "100%", borderRadius: "8px" }} />
        </div>

        {/* Ranked Station Bar Chart */}
        <div className="card" style={{ padding: "0.85rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.65rem" }}>
            <h4 style={{ fontSize: "0.92rem", fontWeight: 700, margin: 0 }}>
              Station PM2.5 Concentrations (Top 20)
            </h4>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Ranked on {selectedDate}
            </span>
          </div>
          <ReactECharts option={rankChartOption} style={{ height: "460px", width: "100%" }} />
        </div>
      </div>

      {/* District Aggregation Summary Table */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <h4 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.75rem" }}>
          District Exposure & Vulnerability Breakdown
        </h4>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" style={{ width: "100%", fontSize: "0.82rem" }}>
            <thead>
              <tr>
                <th>District</th>
                <th>Stations</th>
                <th>District Mean PM2.5</th>
                <th>Peak Station</th>
                <th>Max Exposure</th>
                <th>Corridor Inflow Status</th>
              </tr>
            </thead>
            <tbody>
              {districtRows.map((r) => {
                const isCorridor = r.district.includes("North") || r.district.includes("West");
                return (
                  <tr key={r.district}>
                    <td style={{ fontWeight: 600 }}>{r.district}</td>
                    <td>{r.count}</td>
                    <td style={{ fontWeight: 700, color: r.mean >= 250 ? "#ef4444" : "#f59e0b", fontFamily: "var(--font-mono)" }}>
                      {r.mean} µg/m³
                    </td>
                    <td>{r.maxName}</td>
                    <td style={{ fontFamily: "var(--font-mono)", color: r.max >= 250 ? "#ef4444" : "#f59e0b" }}>
                      {r.max} µg/m³
                    </td>
                    <td>
                      {isCorridor ? (
                        <span className="badge badge-red" style={{ fontSize: "0.72rem" }}>
                          High Inflow Vulnerability
                        </span>
                      ) : (
                        <span className="badge badge-teal" style={{ fontSize: "0.72rem" }}>
                          Secondary / Diluted
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
