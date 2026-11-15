import "cesium/Build/Cesium/Widgets/widgets.css";
import "./style.css";

import {
  BoundingSphere, Cartesian3, Cartographic, Cesium3DTileset, Color, ConstantPositionProperty,
  ConstantProperty, Ellipsoid, EllipsoidGeodesic, HeadingPitchRange, HeightReference, Ion,
  Math as CesiumMath, PinBuilder, PolylineDashMaterialProperty,PolylineGlowMaterialProperty, ScreenSpaceEventHandler,
  ScreenSpaceEventType, VerticalOrigin, Viewer,
} from "cesium";
import { HABITAT, MISSIONS, type Coordinate, type Mission } from "./missions";

// Configuración de Cesium para Marte
(window as any).CESIUM_BASE_URL = "/cesiumStatic";
Ellipsoid.default = Ellipsoid.MARS;
Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN;

const CESIUM_MARS_ASSET_ID = 3644333;

// Vista de la región de estudio: cráter Gale con Mount Sharp al centro
function flyToGale(duration = 3): void {
  viewer.camera.flyTo({
    destination: Cartesian3.fromDegrees(137.8, -8.6, 120_000), 
    orientation: {
      heading: CesiumMath.toRadians(0), 
      pitch: CesiumMath.toRadians(-30), 
      roll: 0,
    },
    duration,
  });
}

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
          <label for="mission">MISSION</label>
          <select id="mission"></select>
        </div>
        <div id="mission-brief" class="result">
          <p class="eyebrow">MISSION BRIEF</p><p>Select a mission to see its objective.</p>
        </div>
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
        <div class="map-overlay"><span class="eyebrow">PLANETARY VIEW</span><span class="map-caption" id="map-caption">Loading Cesium Mars…</span></div>
      </section>
    </section>
    <footer><span>MARTIAN MAP / NASA SPACE APPS CONCEPT</span><span>PROTOTYPE BUILD 0.1.0</span></footer>
  </main>
`;

const apiStatus = document.querySelector<HTMLSpanElement>("#api-status")!;
const planButton = document.querySelector<HTMLButtonElement>("#plan-button")!;
const resultBox = document.querySelector<HTMLDivElement>("#plan-result")!;
const mapCaption = document.querySelector<HTMLSpanElement>("#map-caption")!;

function setResult(
  message: string,
  state: "info" | "warning" | "error" = "info",
) {
  resultBox.dataset.state = state;
  const paragraph = document.createElement("p");
  paragraph.textContent = message;
  resultBox.replaceChildren(
    Object.assign(document.createElement("p"), {
      className: "eyebrow",
      textContent: "PLANNER STATUS",
    }),
    paragraph,
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

    // 1) Pedir la ruta al backend
    let plan: PlanResponse | null = null;
    try {
      const response = await fetch(`${API_BASE_URL}/api/mission/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json() as PlanResponse | { detail: string };
      if (!response.ok) throw new Error("detail" in data ? data.detail : `HTTP ${response.status}`);
      plan = data as PlanResponse;
    } catch (apiError) {
      console.warn("Planner API unavailable, using demo route:", apiError);
    }

    // 2) Ruta real si existe; si no, ruta de ejemplo (DEMO)
    if (plan && plan.status === "planned" && plan.route.length > 1) {
      drawRoute(plan.route, false);
    } else {
      drawRoute(buildDemoRoute(), true);
    }
  } catch (error) {
    setResult(error instanceof Error ? error.message : "Unexpected error.", "error");
  } finally {
    planButton.disabled = false;
    planButton.textContent = "REQUEST ROUTE ANALYSIS";
  }
}
planButton.addEventListener("click", () => void requestPlan());

// ---------- Visor 3D de Marte ----------
const viewer = new Viewer("cesium-container", {
  globe: false, 
  baseLayerPicker: false,
  geocoder: false,
  sceneModePicker: false,
  animation: false,
  timeline: false,
  homeButton: true,
  navigationHelpButton: false,
  infoBox: false,
  selectionIndicator: false,
  fullscreenButton: false,
  shouldAnimate: false,
});

async function loadMars(): Promise<void> {
  try {
    const mars = await Cesium3DTileset.fromIonAssetId(CESIUM_MARS_ASSET_ID, { enableCollision: true });
    viewer.scene.primitives.add(mars);
    mapCaption.textContent = "Cesium Mars · NASA / USGS Astrogeology";
    flyToGale(4);
  } catch (error) {
    mapCaption.textContent = "Could not load Cesium Mars (check ion token)";
    console.error("No se pudo cargar Cesium Mars:", error);
  }
}
void loadMars();


viewer.homeButton.viewModel.command.beforeExecute.addEventListener((event) => {
  event.cancel = true;
  flyToGale();
});





//  Misiones 
// Altura aproximada del terreno en esta zona de Gale (solo para encuadrar la cámara)
const GALE_SURFACE_HEIGHT_M = -4000;

const missionSelect = document.querySelector<HTMLSelectElement>("#mission")!;
const missionBrief = document.querySelector<HTMLDivElement>("#mission-brief")!;

// Bandera/pin del objetivo, pegada al terreno
const targetEntity = viewer.entities.add({
  name: "Mission target",
  show: false,
  position: Cartesian3.fromDegrees(0, 0),
  billboard: {
    image: new PinBuilder().fromColor(Color.fromCssColorString("#f08a4b"), 48),
    verticalOrigin: VerticalOrigin.BOTTOM,
    heightReference: HeightReference.CLAMP_TO_GROUND,
    disableDepthTestDistance: Number.POSITIVE_INFINITY,
  },
});

function renderBrief(mission: Mission): void {
  const totalMass = mission.equipment.reduce((sum, e) => sum + e.massKg, 0);
  const equipment = mission.equipment.map((e) => `${e.item} (${e.massKg} kg)`).join(", ");
  missionBrief.innerHTML = `
    <p class="eyebrow">MISSION BRIEF · ${mission.difficulty.toUpperCase()}</p>
    <p><strong>${mission.objective}</strong></p>
    <p class="muted">${mission.science}</p>
    <p class="muted">Equipment: ${equipment} · Total ${totalMass} kg</p>
    <p class="muted">EVA limit: ${mission.evaMaxHours} h · Target: ${mission.target.label}</p>
  `;
}

function selectMission(mission: Mission): void {
  currentMission = mission;

  const { longitude, latitude } = mission.target;
  renderBrief(mission);

  // El destino del planificador pasa a ser el objetivo de la misión
  document.querySelector<HTMLInputElement>("#end-lon")!.value = String(longitude);
  document.querySelector<HTMLInputElement>("#end-lat")!.value = String(latitude);

  // Mostrar el objetivo y volar hacia él
  targetEntity.position = new ConstantPositionProperty(Cartesian3.fromDegrees(longitude, latitude));
  targetEntity.show = true;
  targetCartesian = Cartesian3.fromDegrees(longitude, latitude);
  updatePreview();
  const oldRoute = viewer.entities.getById("planned-route");
  if (oldRoute) oldRoute.show = false;
  if (!targetCartesian) return;

  viewer.camera.flyToBoundingSphere(
    new BoundingSphere(Cartesian3.fromDegrees(longitude, latitude, GALE_SURFACE_HEIGHT_M), 1500),
    { offset: new HeadingPitchRange(0, CesiumMath.toRadians(-35), 9000), duration: 2.5 }
  );
}

// selector de misiones
missionSelect.innerHTML =
  `<option value="" disabled selected>— Select a mission —</option>` +
  MISSIONS.map((m) => `<option value="${m.id}">${m.name}</option>`).join("");

missionSelect.addEventListener("change", () => {
  const mission = MISSIONS.find((m) => m.id === missionSelect.value);
  if (mission) selectMission(mission);
});










// ---------- Base, astronauta y clic en el mapa ----------
const startLonInput = document.querySelector<HTMLInputElement>("#start-lon")!;
const startLatInput = document.querySelector<HTMLInputElement>("#start-lat")!;

let targetCartesian: Cartesian3 | null = null;
let astronautCartesian = Cartesian3.fromDegrees(HABITAT.longitude, HABITAT.latitude);

// Ícono propio del astronauta (SVG)
const ASTRONAUT_ICON =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
  <circle cx="24" cy="24" r="23" fill="#0f1720" stroke="#ffffff" stroke-width="2"/>
  <rect x="13" y="22" width="6" height="12" rx="2" fill="#cfd8dc"/>
  <rect x="17" y="21" width="14" height="16" rx="4" fill="#ffffff"/>
  <circle cx="24" cy="15" r="7" fill="#ffffff"/>
  <rect x="20" y="12" width="8" height="5" rx="2.5" fill="#f08a4b"/>
  <rect x="18" y="36" width="5" height="6" rx="1.5" fill="#ffffff"/>
  <rect x="25" y="36" width="5" height="6" rx="1.5" fill="#ffffff"/>
</svg>`);

// Base / hábitat
viewer.entities.add({
  name: HABITAT.label,
  position: Cartesian3.fromDegrees(HABITAT.longitude, HABITAT.latitude),
  billboard: {
    image: new PinBuilder().fromText("H", Color.fromCssColorString("#4fa3d9"), 44),
    verticalOrigin: VerticalOrigin.BOTTOM,
    heightReference: HeightReference.CLAMP_TO_GROUND,
    disableDepthTestDistance: Number.POSITIVE_INFINITY,
  },
});

// Astronauta (empieza en la base)
const astronautEntity = viewer.entities.add({
  name: "Astronaut",
  position: astronautCartesian,
  billboard: {
    image: ASTRONAUT_ICON,
    width: 40,
    height: 40,
    verticalOrigin: VerticalOrigin.TOP, 
    heightReference: HeightReference.CLAMP_TO_GROUND,
    disableDepthTestDistance: Number.POSITIVE_INFINITY,
  },
});

// Línea punteada astronauta → objetivo (vista previa, NO es la ruta óptima)
const previewLine = viewer.entities.add({
  name: "Straight-line preview",
  show: false,
  polyline: {
    positions: [],
    width: 3,
    clampToGround: true,
    material: new PolylineDashMaterialProperty({ color: Color.WHITE.withAlpha(0.8), dashLength: 16 }),
  },
});

function updatePreview(): void {
  if (!targetCartesian) return;
  previewLine.polyline!.positions = new ConstantProperty([astronautCartesian, targetCartesian]);
  previewLine.show = true;

  const distanceM = new EllipsoidGeodesic(
    Cartographic.fromCartesian(astronautCartesian),
    Cartographic.fromCartesian(targetCartesian),
    Ellipsoid.MARS
  ).surfaceDistance;

  setResult(
    `Straight-line distance to target: ${(distanceM / 1000).toFixed(2)} km. ` +
      `Press "Request route analysis" to compute the safest route.`,
    "info"
  );
}

function placeAstronaut(cartesian: Cartesian3): void {
  astronautCartesian = cartesian;
  astronautEntity.position = new ConstantPositionProperty(cartesian);

  const carto = Cartographic.fromCartesian(cartesian);
  startLonInput.value = CesiumMath.toDegrees(carto.longitude).toFixed(5);
  startLatInput.value = CesiumMath.toDegrees(carto.latitude).toFixed(5);
  updatePreview();
}

// ---------- Ruta ----------

// Inicio en la base
placeAstronaut(astronautCartesian);
setResult("Select a mission, then click on the terrain to place the astronaut.", "info");

// Clic en el terreno → mover al astronauta ahí
const clickHandler = new ScreenSpaceEventHandler(viewer.scene.canvas);
clickHandler.setInputAction((click: ScreenSpaceEventHandler.PositionedEvent) => {
  if (!viewer.scene.pickPositionSupported) return;
  const picked = viewer.scene.pickPosition(click.position);
  if (picked) placeAstronaut(picked);
}, ScreenSpaceEventType.LEFT_CLICK);
// SUPUESTO: velocidad media caminando con traje y equipo. Acordar el valor con el equipo.
const WALK_SPEED_KMH = 2;

let currentMission: Mission | null = null;

const routeEntity = viewer.entities.add({
  id: "planned-route",
  name: "Planned route",
  show: false,
  polyline: {
    positions: [],
    width: 8,
    clampToGround: true,
    material: new PolylineGlowMaterialProperty({ color: Color.fromCssColorString("#f08a4b"), glowPower: 0.25 }),
  },
});

// Ruta de EJEMPLO: curva suave entre astronauta y objetivo (NO evalúa el terreno)
function buildDemoRoute(): Coordinate[] {
  if (!targetCartesian) throw new Error("Select a mission first.");
  const a = Cartographic.fromCartesian(astronautCartesian);
  const b = Cartographic.fromCartesian(targetCartesian);
  const start = { lon: CesiumMath.toDegrees(a.longitude), lat: CesiumMath.toDegrees(a.latitude) };
  const end = { lon: CesiumMath.toDegrees(b.longitude), lat: CesiumMath.toDegrees(b.latitude) };
  const dLon = end.lon - start.lon;
  const dLat = end.lat - start.lat;

  const points: Coordinate[] = [];
  const steps = 30;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const bend = Math.sin(Math.PI * t) * 0.2; // desvío lateral
    points.push({
      longitude: start.lon + dLon * t - dLat * bend,
      latitude: start.lat + dLat * t + dLon * bend,
    });
  }
  return points;
}

function drawRoute(route: Coordinate[], isDemo: boolean): void {
  const positions = route.map((p) => Cartesian3.fromDegrees(p.longitude, p.latitude));
  routeEntity.polyline!.positions = new ConstantProperty(positions);
  routeEntity.show = true;
  previewLine.show = false;

  // Distancia total sumando cada tramo
  let distanceM = 0;
  for (let i = 1; i < route.length; i++) {
    distanceM += new EllipsoidGeodesic(
      Cartographic.fromDegrees(route[i - 1].longitude, route[i - 1].latitude),
      Cartographic.fromDegrees(route[i].longitude, route[i].latitude),
      Ellipsoid.MARS
    ).surfaceDistance;
  }

  const km = distanceM / 1000;
  const oneWayH = km / WALK_SPEED_KMH;
  const roundTripH = oneWayH * 2; // tiene que volver a la base con oxígeno
  const limit = currentMission?.evaMaxHours;
  const withinLimit = limit === undefined || roundTripH <= limit;

  setResult(
    (isDemo ? "DEMO ROUTE (not computed by the planner yet) · " : "") +
      `Distance ${km.toFixed(2)} km · One-way ≈ ${oneWayH.toFixed(1)} h · ` +
      `Round trip ≈ ${roundTripH.toFixed(1)} h` +
      (limit !== undefined ? ` / EVA limit ${limit} h` : "") +
      (withinLimit ? "" : " · ⚠ EXCEEDS EVA LIMIT"),
    isDemo || !withinLimit ? "warning" : "info"
  );

  // Encuadrar la ruta completa
  const sphere = BoundingSphere.fromPoints(
    route.map((p) => Cartesian3.fromDegrees(p.longitude, p.latitude, GALE_SURFACE_HEIGHT_M))
  );
  viewer.camera.flyToBoundingSphere(sphere, {
    offset: new HeadingPitchRange(0, CesiumMath.toRadians(-50), sphere.radius * 3),
    duration: 2,
  });
}







void checkApi();
