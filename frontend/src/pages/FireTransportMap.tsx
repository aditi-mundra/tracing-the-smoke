import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { Filter, Flame, Compass, Layers, Info, Eye, EyeOff, Radio, Play, Pause, SkipBack, SkipForward, Wind } from "lucide-react";
import { fetchStations, fetchFireHotspots, fetchLiveTelemetry } from "../services/api";
import CalendarDateSelector, { DEFAULT_SHORTCUTS } from "../components/CalendarDateSelector";

const DELHI_COORDS: [number, number] = [28.6139, 77.2090];
const TODAY = new Date().toISOString().split("T")[0];

export default function FireTransportMap() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layersGroupRef = useRef<L.LayerGroup | null>(null);

  const [stations, setStations] = useState<any[]>([]);
  const [fires, setFires] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLiveMode, setIsLiveMode] = useState<boolean>(false);
  const [liveTelemetry, setLiveTelemetry] = useState<any>(null);

  // Filters
  const [selectedDataset, setSelectedDataset] = useState<string>("B2");
  const [selectedDate, setSelectedDate] = useState<string>("2024-11-18");
  const [selectedState, setSelectedState] = useState<string>("All");
  const [filterUpwindOnly, setFilterUpwindOnly] = useState<boolean>(false);
  const [showDistanceRings, setShowDistanceRings] = useState<boolean>(true);
  const [showStations, setShowStations] = useState<boolean>(true);
  const [showPlumeCone, setShowPlumeCone] = useState<boolean>(true);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  useEffect(() => {
    fetchStations().then(setStations).catch(console.error);
  }, []);

  useEffect(() => {
    const effectiveDate = isLiveMode ? TODAY : selectedDate;
    setLoading(true);
    fetchFireHotspots({
      dataset: selectedDataset,
      date: effectiveDate,
      region: selectedState,
      upwind_only: filterUpwindOnly
    })
      .then((data) => {
        if (data && Array.isArray(data)) {
          setFires(data);
        }
      })
      .catch((err) => {
        console.error("fetchFireHotspots error:", err);
      })
      .finally(() => setLoading(false));
  }, [selectedDataset, selectedDate, selectedState, filterUpwindOnly, isLiveMode]);

  // Fetch live telemetry when live mode is activated
  useEffect(() => {
    if (!isLiveMode) return;
    fetchLiveTelemetry()
      .then(setLiveTelemetry)
      .catch((err) => console.warn("live telemetry fetch failed:", err));
    const interval = setInterval(() => {
      fetchLiveTelemetry().then(setLiveTelemetry).catch(console.warn);
    }, 120000); // refresh every 2 min
    return () => clearInterval(interval);
  }, [isLiveMode]);

  // Playback timer for season time-lapse (Oct 15 to Nov 30)
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setSelectedDate((prevDate) => {
        try {
          const dt = new Date(prevDate);
          dt.setDate(dt.getDate() + 1);
          const nextStr = dt.toISOString().split("T")[0];
          if (nextStr > "2024-11-30") {
            return "2024-10-15"; // loop back
          }
          return nextStr;
        } catch {
          return "2024-10-15";
        }
      });
    }, 1400);

    return () => clearInterval(interval);
  }, [isPlaying]);

  const handleStepDay = (delta: number) => {
    try {
      const dt = new Date(selectedDate);
      dt.setDate(dt.getDate() + delta);
      const nextStr = dt.toISOString().split("T")[0];
      if (nextStr >= "2024-10-01" && nextStr <= "2024-12-05") {
        setSelectedDate(nextStr);
      }
    } catch {}
  };

  // Initialize Map with Dark Matter tiles
  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Reset any previous Leaflet ID on the DOM container to avoid re-init crashes
    if ((mapContainerRef.current as any)._leaflet_id) {
      (mapContainerRef.current as any)._leaflet_id = null;
    }

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    // Center on Punjab-Haryana-Delhi transport corridor
    const map = L.map(mapContainerRef.current, {
      zoomControl: true,
      scrollWheelZoom: true
    }).setView([29.95, 76.10], 7);

    // OpenStreetMap Standard Tiles (free, no API key)
    const osmTile = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
      crossOrigin: true
    });

    // Fallback: CartoDB Dark Matter (free, no key for standard use)
    const cartoTile = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19
    });

    osmTile.addTo(map);

    // If OSM tiles fail (rate limit, network issue), fall back to CartoDB automatically
    osmTile.on("tileerror", () => {
      if (map.hasLayer(osmTile)) {
        map.removeLayer(osmTile);
        cartoTile.addTo(map);
      }
    });

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layersGroupRef.current = layerGroup;

    // Trigger immediate and delayed invalidateSize for full container filling
    const t1 = setTimeout(() => map.invalidateSize(), 100);
    const t2 = setTimeout(() => map.invalidateSize(), 400);

    const handleResize = () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize();
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener("resize", handleResize);
      map.remove();
      mapInstanceRef.current = null;
      layersGroupRef.current = null;
    };
  }, []);

  const handleResetView = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([29.95, 76.10], 7);
      mapInstanceRef.current.invalidateSize();
    }
  };

  const handleFitFires = () => {
    if (!mapInstanceRef.current || fires.length === 0) return;
    const coords: [number, number][] = fires
      .map((f) => [f.latitude ?? f.lat, f.longitude ?? f.lon] as [number, number])
      .filter(([lat, lon]) => lat && lon);
    if (coords.length > 0) {
      coords.push(DELHI_COORDS);
      const bounds = L.latLngBounds(coords);
      mapInstanceRef.current.fitBounds(bounds, { padding: [40, 40] });
    }
  };

  // Update Map Layers whenever data changes
  useEffect(() => {
    const layerGroup = layersGroupRef.current;
    const map = mapInstanceRef.current;
    if (!layerGroup || !map) return;

    map.invalidateSize();
    layerGroup.clearLayers();

    // 1. Delhi Receptor Centroid Marker
    const delhiIcon = L.divIcon({
      className: "custom-delhi-beacon",
      html: `
        <div style="position: relative; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; width: 28px; height: 28px; border-radius: 50%; background: rgba(6, 182, 212, 0.35); animation: pulse-emerald 2s infinite;"></div>
          <div style="position: relative; width: 14px; height: 14px; border-radius: 50%; background: #06b6d4; border: 2.5px solid #ffffff; box-shadow: 0 0 14px #06b6d4;"></div>
        </div>
      `,
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });

    const delhiMarker = L.marker(DELHI_COORDS, { icon: delhiIcon });
    delhiMarker.bindPopup(`
      <div style="font-family: inherit; font-size: 0.85rem; color: #0f172a; line-height: 1.5; padding: 4px;">
        <b style="font-size: 0.95rem; color: #0891b2;">Delhi Receptor Centroid</b><br />
        Coordinates: <b>28.6139°N, 77.2090°E</b><br />
        Network: <b>40 eligible CAAQM stations</b> across Delhi NCT<br />
        Mean reporting: <b>34 stations/day</b> • Active daily verification
      </div>
    `);
    layerGroup.addLayer(delhiMarker);

    // 2. Monitoring Stations in Delhi NCT
    if (showStations && stations.length > 0) {
      stations.forEach((st) => {
        const sLat = st.latitude ?? st.lat;
        const sLon = st.longitude ?? st.lon;
        if (sLat && sLon) {
          const stMarker = L.circleMarker([sLat, sLon], {
            radius: 3.5,
            color: "#22d3ee",
            fillColor: "#06b6d4",
            fillOpacity: 0.9,
            weight: 1
          });
          stMarker.bindTooltip(st.station_name ?? st.station_id, {
            direction: "top",
            className: "leaflet-tooltip-dark"
          });
          layerGroup.addLayer(stMarker);
        }
      });
    }

    // 3. Distance Buffer Bands (150 km and 300 km)
    if (showDistanceRings) {
      const ring150 = L.circle(DELHI_COORDS, {
        radius: 150000,
        color: "#06b6d4",
        weight: 1.5,
        fillColor: "#06b6d4",
        fillOpacity: 0.03,
        dashArray: "6, 6"
      });
      ring150.bindTooltip("150 km Inner Transport Ring (High Decay Weight)", { sticky: true });

      const ring300 = L.circle(DELHI_COORDS, {
        radius: 300000,
        color: "#f59e0b",
        weight: 1.5,
        fillColor: "#f59e0b",
        fillOpacity: 0.02,
        dashArray: "6, 6"
      });
      ring300.bindTooltip("300 km Regional Transport Ring", { sticky: true });

      layerGroup.addLayer(ring150);
      layerGroup.addLayer(ring300);
    }

    // 4. North-West Transport Corridor Plume Cone & Advection Streamlines
    if (showPlumeCone) {
      const corridorPolygon = L.polygon(
        [
          DELHI_COORDS,
          [30.2, 73.8],
          [31.8, 74.4],
          [32.2, 75.8],
          [31.0, 77.2],
          [29.5, 77.5]
        ],
        {
          color: "#8b5cf6",
          weight: 1.5,
          dashArray: "6, 6",
          fillColor: "#8b5cf6",
          fillOpacity: 0.05
        }
      );
      corridorPolygon.bindTooltip("North-West Transport Airshed Corridor (315° NW ➔ SE into Delhi)", { sticky: true });
      layerGroup.addLayer(corridorPolygon);

      // Trajectory streamline arcs connecting top upwind fire hotspots directly to Delhi receptor
      const topUpwindFires = fires.filter((f) => f.is_upwind).slice(0, 10);
      topUpwindFires.forEach((f) => {
        const fLat = f.latitude ?? f.lat;
        const fLon = f.longitude ?? f.lon;
        if (fLat && fLon) {
          const line = L.polyline([[fLat, fLon], DELHI_COORDS], {
            color: "#06b6d4",
            weight: 1.4,
            opacity: 0.45,
            dashArray: "4, 6"
          });
          layerGroup.addLayer(line);
        }
      });
    }

    // 5. Fire Hotspots
    fires.forEach((fire) => {
      const lat = fire.latitude ?? fire.lat;
      const lon = fire.longitude ?? fire.lon;
      const frp = fire.frp ?? fire.fire_radiative_power ?? 20;
      const dist = fire.distance_to_delhi_km ?? fire.distance ?? 0;
      const bearing = fire.bearing_to_delhi_deg ?? fire.bearing ?? 0;
      const isUpwind = fire.is_upwind ?? false;

      if (!lat || !lon) return;

      const markerColor = frp >= 80 ? "#ef4444" : frp >= 35 ? "#f97316" : "#f59e0b";
      const radius = frp >= 80 ? 7 : frp >= 35 ? 5.5 : 4;

      const marker = L.circleMarker([lat, lon], {
        radius: radius,
        color: isUpwind ? "#ffffff" : markerColor,
        fillColor: markerColor,
        fillOpacity: 0.88,
        weight: isUpwind ? 1.5 : 0.8
      });

      marker.bindPopup(`
        <div style="font-family: inherit; font-size: 0.82rem; color: #0f172a; line-height: 1.45; padding: 4px;">
          <div style="font-weight: 700; font-size: 0.9rem; color: #b91c1c; margin-bottom: 4px;">
            ${fire.state ?? "Punjab/Haryana"} Active Stubble Fire
          </div>
          Date: <b>${fire.date ?? selectedDate}</b><br />
          FRP (Fire Radiative Power): <b>${Number(frp).toFixed(1)} MW</b><br />
          Distance to Delhi: <b>${Number(dist).toFixed(1)} km</b><br />
          Bearing to Delhi: <b>${Number(bearing).toFixed(1)}°</b><br />
          Upwind Alignment: <b style="color: ${isUpwind ? '#16a34a' : '#64748b'}">${isUpwind ? "YES (Aligned with NW Advection)" : "NO (Crosswind / Neutral)"}</b><br />
          Sensor: <b>VIIRS S-NPP 375m (NASA LANCE)</b>
        </div>
      `);
      layerGroup.addLayer(marker);
    });
  }, [showDistanceRings, showStations, showPlumeCone, fires, stations, selectedDate]);

  const totalFiresCount = fires.length;
  const totalFrp = fires.reduce((acc, f) => acc + (f.frp ?? f.fire_radiative_power ?? 0), 0);
  const upwindCount = fires.filter((f) => f.is_upwind).length;
  const avgDistance =
    totalFiresCount > 0
      ? (
          fires.reduce((acc, f) => acc + (f.distance_to_delhi_km ?? f.distance ?? 0), 0) /
          totalFiresCount
        ).toFixed(0)
      : "—";

  return (
    <div>
      {/* Header */}
      <div className="page-header" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Active Fires &amp; Atmospheric Transport Map</h1>
          <p className="page-subtitle">
            Interactive high-resolution GIS map showing NASA FIRMS VIIRS active fire hotspots, Delhi NCT CAAQM station network, and NW advection corridor.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
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
          <span className="badge badge-cyan">Sensor: VIIRS S-NPP (375m)</span>
          <span className="badge badge-purple">
            {selectedDataset === "B2" ? "B2: Cropland Verified (ESA WorldCover)" : "B1: Regional Boundaries"}
          </span>
          <span className="badge badge-caution">NW Smoke Transport Corridor</span>
        </div>
      </div>

      {/* Live telemetry status bar */}
      {isLiveMode && (
        <div style={{ background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "8px", padding: "0.65rem 1rem", marginBottom: "1.25rem", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "1rem", fontSize: "0.82rem" }}>
          <span style={{ color: "#f87171", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444", display: "inline-block" }} />
            LIVE OPERATIONAL — {TODAY}
          </span>
          {liveTelemetry ? (
            <>
              <span style={{ color: "#94a3b8" }}>Wind: <b style={{ color: "#22d3ee" }}>{liveTelemetry.weather?.wind_speed_ms} m/s @ {liveTelemetry.weather?.wind_direction_deg}°</b></span>
              <span style={{ color: "#94a3b8" }}>BLH: <b style={{ color: "#a78bfa" }}>{liveTelemetry.weather?.boundary_layer_height_m} m</b></span>
              <span style={{ color: "#94a3b8" }}>Live PM2.5 Est: <b style={{ color: "#fb923c" }}>{liveTelemetry.air_quality_telemetry?.live_estimated_pm25} µg/m³</b></span>
              <span style={{ color: "#94a3b8" }}>Risk: <b style={{ color: "#f87171" }}>{liveTelemetry.transport_analysis?.smoke_transport_risk}</b></span>
            </>
          ) : (
            <span style={{ color: "#64748b" }}>Fetching live atmospheric data from Open-Meteo NWP…</span>
          )}
        </div>
      )}

      {/* Date Calendar Picker (hidden in live mode) */}
      {!isLiveMode && (
        <div className="card" style={{ marginBottom: "1.25rem", padding: "0.85rem 1.15rem" }}>
          <CalendarDateSelector
            value={selectedDate}
            onChange={setSelectedDate}
            minDate="2018-01-01"
            maxDate="2025-12-31"
            label="Observation Date"
            helperText="Select any calendar date to inspect satellite active fire detections across Punjab and Haryana."
            shortcuts={DEFAULT_SHORTCUTS}
          />
        </div>
      )}

      {/* Live mode date banner */}
      {isLiveMode && (
        <div className="card" style={{ marginBottom: "1.25rem", padding: "0.75rem 1rem", background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.2)", display: "flex", alignItems: "center", gap: "0.65rem" }}>
          <Info size={16} color="#f87171" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: "0.82rem", color: "#94a3b8" }}>
            Showing fire thermal anomaly detections nearest to <b style={{ color: "#f87171" }}>{TODAY} (TODAY)</b>.
            Live VIIRS FIRMS passes are archived with ~3–6h latency. Most recent orbital overpass cluster is displayed.
          </span>
        </div>
      )}

      {/* Interactive Filter Dock */}
      <div
        className="card"
        style={{
          marginBottom: "1.25rem",
          display: "flex",
          gap: "1.25rem",
          flexWrap: "wrap",
          alignItems: "center",
          padding: "0.85rem 1.15rem"
        }}
      >
        {/* Dataset Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
          <Layers size={16} color="var(--accent-purple)" />
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-secondary)" }}>Dataset:</span>
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            style={{
              background: "var(--bg-secondary)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-color)",
              padding: "0.35rem 0.65rem",
              borderRadius: "6px",
              fontSize: "0.82rem",
              fontFamily: "inherit",
              outline: "none"
            }}
          >
            <option value="B2">B2 — ESA WorldCover Cropland Intersected (Primary Study)</option>
            <option value="B1">B1 — Raw Regional Envelopes (Reference)</option>
          </select>
        </div>

        {/* State Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
          <Filter size={16} color="var(--accent-teal)" />
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-secondary)" }}>Region:</span>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            style={{
              background: "var(--bg-secondary)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-color)",
              padding: "0.35rem 0.65rem",
              borderRadius: "6px",
              fontSize: "0.82rem",
              fontFamily: "inherit",
              outline: "none"
            }}
          >
            <option value="All">All (Punjab & Haryana)</option>
            <option value="Punjab">Punjab Only</option>
            <option value="Haryana">Haryana Only</option>
          </select>
        </div>

        {/* Upwind toggle */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.45rem",
            cursor: "pointer",
            fontSize: "0.82rem",
            color: filterUpwindOnly ? "var(--accent-cyan)" : "var(--text-secondary)",
            fontWeight: 500
          }}
        >
          <input
            type="checkbox"
            checked={filterUpwindOnly}
            onChange={(e) => setFilterUpwindOnly(e.target.checked)}
          />
          <span>Upwind Corridor Only (NW Advection)</span>
        </label>

        {/* Distance Rings toggle */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.45rem",
            cursor: "pointer",
            fontSize: "0.82rem",
            color: "var(--text-secondary)",
            fontWeight: 500
          }}
        >
          <input
            type="checkbox"
            checked={showDistanceRings}
            onChange={(e) => setShowDistanceRings(e.target.checked)}
          />
          <span>Distance Rings (150 & 300 km)</span>
        </label>

        {/* Plume Corridor toggle */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.45rem",
            cursor: "pointer",
            fontSize: "0.82rem",
            color: showPlumeCone ? "var(--accent-purple)" : "var(--text-secondary)",
            fontWeight: 500
          }}
        >
          <input
            type="checkbox"
            checked={showPlumeCone}
            onChange={(e) => setShowPlumeCone(e.target.checked)}
          />
          <span>NW Plume Corridor & Streamlines</span>
        </label>

        {/* Stations toggle */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.45rem",
            cursor: "pointer",
            fontSize: "0.82rem",
            color: "var(--text-secondary)",
            fontWeight: 500
          }}
        >
          <input
            type="checkbox"
            checked={showStations}
            onChange={(e) => setShowStations(e.target.checked)}
          />
          <span>Delhi CAAQM Stations ({stations.length})</span>
        </label>
      </div>

      {/* Season Playback & Time-Lapse Player (Historical Mode only) */}
      {!isLiveMode && (
      <div
        className="card"
        style={{
          marginBottom: "1.25rem",
          padding: "0.85rem 1.15rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "1rem",
          background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)",
          border: "1px solid rgba(6, 182, 212, 0.25)"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            style={{
              background: isPlaying ? "rgba(239, 68, 68, 0.2)" : "rgba(6, 182, 212, 0.2)",
              border: `1px solid ${isPlaying ? "#ef4444" : "#06b6d4"}`,
              color: isPlaying ? "#f87171" : "#22d3ee",
              borderRadius: "8px",
              padding: "0.45rem 0.9rem",
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              fontWeight: 700,
              fontSize: "0.82rem",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
          >
            {isPlaying ? <Pause size={15} /> : <Play size={15} />}
            <span>{isPlaying ? "Pause Season" : "Play Stubble Season"}</span>
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <button
              onClick={() => handleStepDay(-1)}
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                color: "var(--text-secondary)",
                borderRadius: "6px",
                padding: "0.4rem",
                cursor: "pointer"
              }}
              title="Previous Day"
            >
              <SkipBack size={14} />
            </button>
            <button
              onClick={() => handleStepDay(1)}
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                color: "var(--text-secondary)",
                borderRadius: "6px",
                padding: "0.4rem",
                cursor: "pointer"
              }}
              title="Next Day"
            >
              <SkipForward size={14} />
            </button>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flex: 1, minWidth: "260px" }}>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
            Oct 15 (Early Harvest)
          </div>
          <input
            type="range"
            min={0}
            max={46}
            value={Math.max(
              0,
              Math.min(
                46,
                Math.round(
                  (new Date(selectedDate).getTime() - new Date("2024-10-15").getTime()) / (1000 * 3600 * 24)
                ) || 0
              )
            )}
            onChange={(e) => {
              const d = new Date("2024-10-15");
              d.setDate(d.getDate() + Number(e.target.value));
              setSelectedDate(d.toISOString().split("T")[0]);
            }}
            style={{ flex: 1, accentColor: "var(--accent-cyan)", cursor: "pointer" }}
          />
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
            Nov 30 (Season End)
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span className="badge badge-purple" style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>
            {selectedDate}
          </span>
          <span className="badge badge-amber" style={{ fontSize: "0.78rem" }}>
            {totalFiresCount} Detections
          </span>
        </div>
      </div>
      )}

      {/* Snapshot Summary Bar */}
      <div className="card-grid" style={{ marginBottom: "1.25rem" }}>
        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Active Thermal Anomalies</span>
            <div className="kpi-icon-wrap">
              <Flame size={16} color="var(--accent-amber)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-amber)" }}>
            {totalFiresCount}
          </div>
          <div className="kpi-subtitle">
            Detections on {selectedDate} ({selectedState})
          </div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Cumulative Fire Radiative Power</span>
            <div className="kpi-icon-wrap">
              <Radio size={16} color="var(--accent-red)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "#f87171" }}>
            {totalFrp.toLocaleString(undefined, { maximumFractionDigits: 1 })}{" "}
            <span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: 400 }}>MW</span>
          </div>
          <div className="kpi-subtitle">Thermal emission intensity</div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Upwind Smoke Alignment</span>
            <div className="kpi-icon-wrap">
              <Compass size={16} color="var(--accent-emerald)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-emerald)" }}>
            {totalFiresCount > 0 ? ((upwindCount / totalFiresCount) * 100).toFixed(1) : 0}%
          </div>
          <div className="kpi-subtitle">{upwindCount} hotspots oriented directly towards Delhi</div>
        </div>

        <div className="card card-kpi">
          <div className="kpi-header">
            <span className="kpi-title">Mean Distance to Delhi</span>
            <div className="kpi-icon-wrap">
              <Compass size={16} color="var(--accent-cyan)" />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "var(--accent-cyan)" }}>
            {avgDistance}{" "}
            <span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: 400 }}>km</span>
          </div>
          <div className="kpi-subtitle">From Delhi receptor centroid (28.61°N, 77.21°E)</div>
        </div>
      </div>

      {/* Nearest sample notification if requested date has no direct orbital observations */}
      {fires.length > 0 && fires[0]?.is_nearest_sample && (
        <div
          style={{
            marginBottom: "1.25rem",
            padding: "0.75rem 1.15rem",
            borderRadius: "8px",
            background: "rgba(245, 158, 11, 0.12)",
            border: "1px solid rgba(245, 158, 11, 0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "0.85rem",
            color: "#f59e0b"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
            <Info size={18} />
            <span>
              Observation date <b>{selectedDate}</b> has no direct satellite overpasses in the test window. Displaying nearest calibrated observation cluster from <b>{fires[0].sample_date}</b>.
            </span>
          </div>
          <button
            onClick={() => setSelectedDate(fires[0].sample_date)}
            style={{
              background: "rgba(245, 158, 11, 0.2)",
              border: "1px solid rgba(245, 158, 11, 0.4)",
              color: "#fbbf24",
              borderRadius: "4px",
              padding: "0.25rem 0.65rem",
              fontSize: "0.78rem",
              cursor: "pointer",
              fontWeight: 600
            }}
          >
            Switch to {fires[0].sample_date}
          </button>
        </div>
      )}

      {/* Leaflet Map Box */}
      <div className="chart-box" style={{ padding: "0.5rem", position: "relative" }}>
        {/* Map Floating Control Toolbar */}
        <div
          style={{
            position: "absolute",
            top: "16px",
            right: "16px",
            zIndex: 1000,
            display: "flex",
            gap: "0.5rem",
            background: "rgba(15, 23, 42, 0.85)",
            backdropFilter: "blur(8px)",
            padding: "0.35rem 0.5rem",
            borderRadius: "8px",
            border: "1px solid rgba(255, 255, 255, 0.1)"
          }}
        >
          <button
            onClick={handleResetView}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-secondary)",
              fontSize: "0.78rem",
              cursor: "pointer",
              padding: "0.25rem 0.5rem",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem"
            }}
            title="Reset map view to Punjab-Delhi Corridor"
          >
            <Compass size={14} color="var(--accent-teal)" />
            <span>Reset View</span>
          </button>
          <div style={{ width: "1px", background: "rgba(255, 255, 255, 0.1)" }} />
          <button
            onClick={handleFitFires}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-secondary)",
              fontSize: "0.78rem",
              cursor: "pointer",
              padding: "0.25rem 0.5rem",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem"
            }}
            title="Fit zoom to current fire hotspots and Delhi"
          >
            <Layers size={14} color="var(--accent-cyan)" />
            <span>Fit Extent</span>
          </button>
        </div>

        {/* Loading Overlay */}
        {loading && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(10, 15, 29, 0.45)",
              backdropFilter: "blur(2px)",
              zIndex: 999,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "10px"
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.75rem 1.25rem",
                background: "var(--bg-card)",
                borderRadius: "8px",
                border: "1px solid var(--border-color)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.4)"
              }}
            >
              <div
                style={{
                  width: "16px",
                  height: "16px",
                  border: "2px solid var(--accent-cyan)",
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite"
                }}
              />
              <span style={{ fontSize: "0.85rem", color: "var(--text-primary)", fontWeight: 500 }}>
                Loading satellite active fires...
              </span>
            </div>
          </div>
        )}

        <div ref={mapContainerRef} style={{ height: "560px", width: "100%", borderRadius: "10px" }} />
      </div>

      {/* Physics & Feature Engineering Documentation */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "1.25rem",
          marginTop: "1.25rem"
        }}
      >
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.65rem" }}>
            <Compass size={18} color="var(--accent-teal)" />
            <h4 style={{ fontSize: "0.92rem", fontWeight: 700, color: "var(--text-primary)" }}>
              Atmospheric Transport & Advection Physics
            </h4>
          </div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            In meteorological coordinate standards, wind direction signifies <b>the direction FROM which the wind blows</b>.
            During post-monsoon harvest (October–November), the Indo-Gangetic Plain is dominated by north-westerly surface flows (290°–330° FROM NW, propagating TO SE).
            Upwind alignment is evaluated as <code>max(0, cos(θ_bearing - θ_wind))</code>, capturing fire plumes oriented along the direct trajectory towards the Delhi receptor.
          </p>
        </div>

        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.65rem" }}>
            <Flame size={18} color="var(--accent-amber)" />
            <h4 style={{ fontSize: "0.92rem", fontWeight: 700, color: "var(--text-primary)" }}>
              Distance Decay Weighting Heuristic
            </h4>
          </div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            Atmospheric dispersion and dry deposition are parameterized using a non-linear decay function:
            <code>w(d) = 1 / (1 + (d / 150 km)^1.5)</code>.
            Fires within the 150 km inner buffer exert a stronger mathematical push in the feature matrix, while distant plumes (&gt; 300 km) undergo lateral diffusion and dilution.
          </p>
        </div>
      </div>
    </div>
  );
}
