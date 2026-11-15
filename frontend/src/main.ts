import "cesium/Build/Cesium/Widgets/widgets.css";
import "./style.css";
import { Cartesian3, Color, Math as CesiumMath, Viewer } from "cesium";

type RouteProfile = "direct" | "low_slope" | "conservative";

interface PlanResponse {
  status: string;
  profile: RouteProfile;
  message: string;
  route: Array<{ longitude: number; latitude: number }>;
  distance_m: number | null;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Could not find #app root element.");

app.innerHTML = `
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark">M</span>
        <div><p class="eyebrow">MISSION CONTROL / 01</p><h1>MARTIAN MAP</h1></div>
      </div>
      <div class="system-status"><span class="status-dot"></span><span id="api-status">CONNECTING API</span></div>
    </header>
    <section class="workspace">
      <aside class="panel">
        <p class="eyebrow">EXPLORATION TOOLS</p>
        <h2>Mission planner</h2>
        <p class="muted">Explore a study area and prepare a terrain-aware traverse.</p>
        <div class="field">
          <label for="profile">ROUTE PROFILE</label>
          <select id="profile">
            <option value="direct">Direct</option>
            <option value="low_slope" selected>Low slope</option>
            <option value="conservative">Conservative</option>
          </select>
        </div>
        <div class="coordinate-grid">
          <div class="field"><label for="start-lon">START LONGITUDE</label><input id="start-lon" type="number" step="any" value="137.4" /></div>
          <div class="field"><label for="start-lat">START LATITUDE</label><input id="start-lat" type="number" step="any" value="-4.6" /></div>
          <div class="field"><label for="end-lon">DEST. LONGITUDE</label><input id="end-lon" type="number" step="any" value="137.5" /></div>
          <div class="field"><label for="end-lat">DEST. LATITUDE</label><input id="end-lat" type="number" step="any" value="-4.7" /></div>
        </div>
        <button id="plan-button" class="primary-button">REQUEST ROUTE ANALYSIS</button>
        <div id="plan-result" class="result" role="status">
          <p class="eyebrow">PLANNER STATUS</p><p>Awaiting mission parameters.</p>
        </div>
        <div class="notice"><strong>DATA LIMITATION</strong><p>Orbital elevation data cannot guarantee surface traversability or detect every local hazard.</p></div>
      </aside>
      <section class="map-panel" aria-label="3D globe">
        <div id="cesium-container"></div>
        <div class="map-overlay"><span class="eyebrow">PLANETARY VIEW</span><span class="map-caption">Cesium starter globe · Mars data not connected</span></div>
      </section>
    </section>
    <footer><span>MARTIAN MAP / NASA SPACE APPS CONCEPT</span><span>PROTOTYPE BUILD 0.1.0</span></footer>
  </main>
`;

const apiStatus = document.querySelector<HTMLSpanElement>("#api-status")!;
const planButton = document.querySelector<HTMLButtonElement>("#plan-button")!;
const resultBox = document.querySelector<HTMLDivElement>("#plan-result")!;

function setResult(message: string, state: "info" | "warning" | "error" = "info") {
  resultBox.dataset.state = state;
  const paragraph = document.createElement("p");
  paragraph.textContent = message;
  resultBox.replaceChildren(
    Object.assign(document.createElement("p"), { className: "eyebrow", textContent: "PLANNER STATUS" }),
    paragraph
  );
}

async function checkApi(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    apiStatus.textContent = "API ONLINE";
    apiStatus.dataset.state = "online";
    const missionResponse = await fetch(`${API_BASE_URL}/api/mission`);
    if (!missionResponse.ok) throw new Error("Mission endpoint unavailable");
    console.info("Mission metadata:", await missionResponse.json());
  } catch (error) {
    apiStatus.textContent = "API OFFLINE";
    apiStatus.dataset.state = "offline";
    console.error("API health check failed:", error);
  }
}

function readNumber(id: string): number {
  const input = document.querySelector<HTMLInputElement>(`#${id}`)!;
  const value = Number(input.value);
  if (!Number.isFinite(value)) throw new Error(`Invalid value for ${id}`);
  return value;
}

async function requestPlan(): Promise<void> {
  planButton.disabled = true;
  planButton.textContent = "ANALYZING…";
  try {
    const profile = document.querySelector<HTMLSelectElement>("#profile")!.value as RouteProfile;
    const payload = {
      start: { longitude: readNumber("start-lon"), latitude: readNumber("start-lat") },
      destination: { longitude: readNumber("end-lon"), latitude: readNumber("end-lat") },
      profile
    };
    const response = await fetch(`${API_BASE_URL}/api/mission/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json() as PlanResponse | { detail: string };
    if (!response.ok) throw new Error("detail" in data ? data.detail : `HTTP ${response.status}`);
    const plan = data as PlanResponse;
    setResult(plan.message, plan.status === "planned" ? "info" : "warning");
  } catch (error) {
    setResult(error instanceof Error ? error.message : "Unexpected error.", "error");
  } finally {
    planButton.disabled = false;
    planButton.textContent = "REQUEST ROUTE ANALYSIS";
  }
}
planButton.addEventListener("click", () => void requestPlan());

const viewer = new Viewer("cesium-container", {
  animation: false,
  timeline: false,
  baseLayerPicker: false,
  geocoder: false,
  homeButton: true,
  sceneModePicker: false,
  navigationHelpButton: false,
  infoBox: false,
  selectionIndicator: false,
  fullscreenButton: false,
  shouldAnimate: false
});
viewer.camera.setView({
  destination: Cartesian3.fromDegrees(0, 15, 20_000_000),
  orientation: { heading: 0, pitch: CesiumMath.toRadians(-90), roll: 0 }
});
// Example marker only. These coordinates are not connected to a Mars dataset.
viewer.entities.add({
  name: "Example study point",
  position: Cartesian3.fromDegrees(137.4, -4.6, 0),
  point: { pixelSize: 8, color: Color.ORANGE, outlineColor: Color.WHITE, outlineWidth: 2 }
});
void checkApi();
