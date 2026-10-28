/**
 * API client service for communicating with FastAPI backend endpoints.
 * Resilient to port variations (automatically checks 8000 and falls back to 8001).
 */

let API_BASE = (import.meta.env.VITE_API_BASE as string) || "http://127.0.0.1:8000/api";

async function apiFetch(endpoint: string, options?: RequestInit): Promise<Response> {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    return res;
  } catch (err) {
    // If running locally on default 8000 and socket failed, auto-fallback to 8001
    if (API_BASE.includes(":8000")) {
      const fallback = API_BASE.replace(":8000", ":8001");
      try {
        const res2 = await fetch(`${fallback}${endpoint}`, options);
        if (res2.ok) {
          API_BASE = fallback;
          return res2;
        }
      } catch {
        // Fallback also failed, re-throw initial error
      }
    }
    throw err;
  }
}

export async function fetchOverview(date?: string) {
  const url = date ? `/overview?date=${encodeURIComponent(date)}` : "/overview";
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch overview");
  return res.json();
}

export async function fetchAvailableDates() {
  const res = await apiFetch("/dates");
  if (!res.ok) throw new Error("Failed to fetch available dates");
  return res.json();
}

export async function fetchMetadata() {
  const res = await apiFetch("/metadata");
  if (!res.ok) throw new Error("Failed to fetch metadata");
  return res.json();
}

export async function fetchStations() {
  const res = await apiFetch("/stations");
  if (!res.ok) throw new Error("Failed to fetch stations");
  return res.json();
}

export async function fetchPollution(year?: number) {
  const url = year ? `/pollution?year=${year}` : "/pollution";
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch pollution data");
  return res.json();
}

export async function fetchFires(year?: number) {
  const url = year ? `/fires?year=${year}` : "/fires";
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch fire data");
  return res.json();
}

export async function fetchFireHotspots(params?: { dataset?: string; date?: string; region?: string; upwind_only?: boolean }) {
  let url = "/fires/hotspots";
  if (params) {
    const q = new URLSearchParams();
    if (params.dataset) q.append("dataset", params.dataset);
    if (params.date) q.append("date", params.date);
    if (params.region) q.append("region", params.region);
    if (params.upwind_only !== undefined) q.append("upwind_only", String(params.upwind_only));
    url += `?${q.toString()}`;
  }
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch fire hotspots");
  return res.json();
}

export async function fetchWeather(year?: number) {
  const url = year ? `/weather?year=${year}` : "/weather";
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch weather data");
  return res.json();
}

export async function fetchModels() {
  const res = await apiFetch("/models");
  if (!res.ok) throw new Error("Failed to fetch models");
  return res.json();
}

export async function fetchEvaluation() {
  const res = await apiFetch("/evaluation");
  if (!res.ok) throw new Error("Failed to fetch evaluation metrics");
  return res.json();
}

export async function fetchFeatureComparison() {
  const res = await apiFetch("/feature-comparison");
  if (!res.ok) throw new Error("Failed to fetch feature comparison");
  return res.json();
}

export async function fetchShapGlobal() {
  const res = await apiFetch("/shap/global");
  if (!res.ok) throw new Error("Failed to fetch global SHAP data");
  return res.json();
}

export async function fetchShapDay(dateStr: string) {
  const res = await apiFetch(`/shap/day/${dateStr}`);
  if (!res.ok) throw new Error(`Failed to fetch SHAP explanation for ${dateStr}`);
  return res.json();
}

export async function fetchEpisodes() {
  const res = await apiFetch("/episodes");
  if (!res.ok) throw new Error("Failed to fetch severe episodes");
  return res.json();
}

export async function postPredict(payload: {
  mode: string;
  date?: string;
  model_name: string;
  features?: Record<string, number>;
}) {
  const res = await apiFetch("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Prediction request failed");
  return res.json();
}

export async function fetchLiveTelemetry() {
  const res = await apiFetch("/live/telemetry");
  if (!res.ok) throw new Error("Failed to fetch live telemetry");
  return res.json();
}

export async function triggerLiveRefresh() {
  const res = await apiFetch("/live/refresh", { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger live refresh");
  return res.json();
}

export async function fetchCounterfactualSimulation(payload: {
  date: string;
  punjab_abatement_pct: number;
  haryana_abatement_pct: number;
  wind_speed_multiplier?: number;
  blh_multiplier?: number;
  model_name?: string;
}) {
  const res = await apiFetch("/simulate/counterfactual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Counterfactual simulation failed");
  return res.json();
}

export async function fetchSpatialStations(date?: string) {
  const url = date ? `/stations/spatial?date=${encodeURIComponent(date)}` : "/stations/spatial";
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch spatial station gradient");
  return res.json();
}


