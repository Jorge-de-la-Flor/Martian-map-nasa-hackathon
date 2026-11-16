import "cesium/Build/Cesium/Widgets/widgets.css";
import "./style.css";

import {
  BoundingSphere,Cartesian2, Cartesian3, Cartographic, Cesium3DTileset, Color, ConstantPositionProperty,
  ConstantProperty, Ellipsoid, EllipsoidGeodesic, HeadingPitchRange, HeightReference, Ion,
  Math as CesiumMath, PinBuilder, PolylineDashMaterialProperty,PolylineGlowMaterialProperty, Rectangle, ScreenSpaceEventHandler,
  ScreenSpaceEventType, VerticalOrigin, Viewer,
} from "cesium";
import { HABITAT, MISSIONS, STUDY_ZONE, isInsideZone, type Coordinate, type Mission } from "./missions";
import {
  GALE_ENVIRONMENT, RADIATION_MSV_PER_HOUR, airTempAt, batteryDrainPerHour, heartRateBpm,
  levelFromAirTemp, levelFromHeartRate, levelFromPercent, o2Multiplier, type Level,
} from "./environment";

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

// Respuesta de POST /api/mission/plan/geo (A* sobre el DEM real de Gale)
interface RouteMetrics {
  distance_m: number;
  ascent_m: number;
  descent_m: number;
  max_slope_deg: number;
  mean_slope_deg: number;
  duration_s: number | null;
}

interface GeoPlanResponse {
  status: "planned";
  profile: RouteProfile;
  message: string;
  route_geo: Array<{ longitude: number; latitude: number; elevation_m: number; slope_deg: number }>;
  elevation_profile: Array<{ distance_m: number; elevation_m: number; slope_deg: number }>;
  metrics: RouteMetrics;
  limitations: string[];
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
          <label for="eva-start">EVA START · LOCAL MARS TIME</label>
          <select id="eva-start">
            <option value="6">06:00 · dawn</option>
            <option value="8">08:00</option>
            <option value="10" selected>10:00</option>
            <option value="12">12:00 · noon</option>
            <option value="14">14:00</option>
            <option value="16">16:00</option>
            <option value="18">18:00 · dusk</option>
          </select>
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
                <button id="traverse-button" class="primary-button secondary-button" disabled>▶ START TRAVERSE</button>
        <div id="plan-result" class="result" role="status">
          <p class="eyebrow">PLANNER STATUS</p><p>Awaiting mission parameters.</p>
        </div>
        <div class="notice"><strong>DATA LIMITATION</strong><p>Orbital elevation data cannot guarantee surface traversability or detect every local hazard.</p></div>
      </aside>
      <section class="map-panel" aria-label="3D globe">
        <div id="cesium-container"></div>
                <div id="telemetry" class="telemetry">
          <p class="eyebrow">SUIT TELEMETRY</p>
          <div class="tm-row" id="tm-o2"><span>O₂ left</span><strong>—</strong><em>SIM</em></div>
          <div class="tm-row" id="tm-hr"><span>Heart rate</span><strong>—</strong><em>SIM</em></div>
          <div class="tm-row" id="tm-battery"><span>Suit battery</span><strong>—</strong><em>SIM</em></div>
          <div class="tm-row" id="tm-air"><span>Air temp</span><strong>—</strong><em>REMS</em></div>
          <div class="tm-row" id="tm-pressure"><span>Pressure</span><strong>—</strong><em>REMS</em></div>
          <div class="tm-row" id="tm-radiation"><span>Radiation dose</span><strong>—</strong><em>RAD</em></div>
        </div>
                <div id="route-profile" class="route-profile" hidden>
          <p class="eyebrow">ELEVATION PROFILE · REAL TERRAIN</p>
          <canvas id="profile-chart" width="620" height="300" role="img" aria-label="Elevation profile of the planned route"></canvas>
          <p id="profile-caption" class="muted"></p>
          <p class="profile-legend">Line color = slope: <span style="color:#7fb3d5">&lt;5°</span> · <span style="color:#65a39e">5–10°</span> · <span style="color:#e8bb69">10–20°</span> · <span style="color:#e46549">≥20°</span></p>
        </div>
        <div id="site-photo" class="site-photo" hidden>
          <button id="site-photo-close" class="site-photo-close" aria-label="Close">×</button>
          <img id="site-photo-img" alt="" />
          <p class="eyebrow">ARRIVAL VIEW · REAL IMAGE</p>
          <p id="site-photo-caption"></p>
          <p id="site-photo-credit" class="site-photo-credit"></p>
        </div>
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

        if (!isInsideZone(payload.start.longitude, payload.start.latitude)) {
      throw new Error(
        "⚠ OUTSIDE STUDY ZONE · The start point must be inside the blue dashed zone to plan a route."
      );
    }

    // 1) Pedir la ruta real al backend (A* sobre el DEM de Gale)
    let plan: GeoPlanResponse | null = null;
    let response: Response | null = null;
    try {
      response = await fetch(`${API_BASE_URL}/api/mission/plan/geo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, walking_speed_m_s: WALK_SPEED_KMH / 3.6 }),
      });
    } catch (networkError) {
      console.warn("Planner API unreachable, using demo route:", networkError);
    }

    if (response) {
      const data = (await response.json()) as GeoPlanResponse | { detail: unknown };
      if (!response.ok) {
        // El backend respondió pero rechazó la ruta: mostrar el motivo (no dibujar DEMO)
        const detail =
          "detail" in data && typeof data.detail === "string" ? data.detail : `HTTP ${response.status}`;
        throw new Error(`⚠ PLANNER · ${detail}`);
      }
      plan = data as GeoPlanResponse;
    }

    // 2) Ruta real si el backend respondió; si está apagado, ruta DEMO
    if (plan && plan.status === "planned" && plan.route_geo.length > 1) {
      drawRoute(plan.route_geo, false, plan.metrics);
      showElevationProfile(plan.elevation_profile, plan.metrics);
    } else {
      drawRoute(buildDemoRoute(), true);
      hideElevationProfile();
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
const GALE_SURFACE_HEIGHT_M = -3550; // boxwork ≈ -3610 m, Nazca ≈ -3488 m (DEM USGS)

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

// Miniatura de la foto real, flotando sobre el sitio
const targetPhotoEntity = viewer.entities.add({
  name: "Target photo",
  show: false,
  position: Cartesian3.fromDegrees(0, 0),
  billboard: {
    width: 160,
    height: 100,
    verticalOrigin: VerticalOrigin.BOTTOM,
    pixelOffset: new Cartesian2(0, -56), // encima del pin
    heightReference: HeightReference.CLAMP_TO_GROUND,
    disableDepthTestDistance: Number.POSITIVE_INFINITY,
  },
  label: {
    text: "",
    font: "bold 12px sans-serif",
    fillColor: Color.WHITE,
    showBackground: true,
    backgroundColor: Color.fromCssColorString("#0c121a").withAlpha(0.85),
    verticalOrigin: VerticalOrigin.BOTTOM,
    pixelOffset: new Cartesian2(0, -162), // encima de la foto
    heightReference: HeightReference.CLAMP_TO_GROUND,
    disableDepthTestDistance: Number.POSITIVE_INFINITY,
  },
});

// Carga la foto y le pone un borde naranja (recortada sin deformarse)
function loadFramedPhoto(src: string): Promise<HTMLCanvasElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const w = 320, h = 200, border = 6;
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d")!;
      ctx.fillStyle = "#f08a4b";
      ctx.fillRect(0, 0, w, h);
      const innerW = w - 2 * border, innerH = h - 2 * border;
      const scale = Math.max(innerW / img.width, innerH / img.height) * 1.4; // zoom al centro
      const sw = innerW / scale, sh = innerH / scale;
      ctx.drawImage(img, (img.width - sw) / 2, (img.height - sh) / 2, sw, sh, border, border, innerW, innerH);
      resolve(canvas);
    };
    img.onerror = reject;
    img.src = src;
  });
}

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
    resetTelemetry();

  const { longitude, latitude } = mission.target;
  renderBrief(mission);

  // El destino del planificador pasa a ser el objetivo de la misión
  document.querySelector<HTMLInputElement>("#end-lon")!.value = String(longitude);
  document.querySelector<HTMLInputElement>("#end-lat")!.value = String(latitude);

  // Mostrar el objetivo y volar hacia él
  targetEntity.position = new ConstantPositionProperty(Cartesian3.fromDegrees(longitude, latitude));
  targetEntity.show = true;

    targetPhotoEntity.position = new ConstantPositionProperty(Cartesian3.fromDegrees(longitude, latitude));
  targetPhotoEntity.label!.text = new ConstantProperty(mission.target.label);
  loadFramedPhoto(mission.photo.src)
    .then((canvas) => {
      targetPhotoEntity.billboard!.image = new ConstantProperty(canvas);
      targetPhotoEntity.show = true;
    })
    .catch((error) => console.error("Could not load site photo:", error));
  targetCartesian = Cartesian3.fromDegrees(longitude, latitude);

  // El rover presurizado deja al astronauta dentro del área con datos de terreno
  placeAstronaut(Cartesian3.fromDegrees(mission.roverDrop.longitude, mission.roverDrop.latitude));
    
 

  // Encuadrar el punto de bajada del rover y el objetivo
  const missionArea = BoundingSphere.fromPoints([
    Cartesian3.fromDegrees(mission.roverDrop.longitude, mission.roverDrop.latitude, GALE_SURFACE_HEIGHT_M),
    Cartesian3.fromDegrees(longitude, latitude, GALE_SURFACE_HEIGHT_M),
  ]);
  viewer.camera.flyToBoundingSphere(missionArea, {
    offset: new HeadingPitchRange(0, CesiumMath.toRadians(-40), Math.max(missionArea.radius * 4, 1500)),
    duration: 2.5,
  });
    
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



// Zona de estudio = área con datos de elevación (se actualiza con /api/mission/coverage)
function zoneOutline(): Cartesian3[] {
  const { west, south, east, north } = STUDY_ZONE;
  return Cartesian3.fromDegreesArray([west, south, east, south, east, north, west, north, west, south]);
}

const zoneFill = viewer.entities.add({
  name: STUDY_ZONE.label,
  rectangle: {
    coordinates: Rectangle.fromDegrees(STUDY_ZONE.west, STUDY_ZONE.south, STUDY_ZONE.east, STUDY_ZONE.north),
    material: Color.fromCssColorString("#4fa3d9").withAlpha(0.08),
  },
});
const zoneBorder = viewer.entities.add({
  name: `${STUDY_ZONE.label} border`,
  polyline: {
    positions: zoneOutline(),
    width: 2,
    clampToGround: true,
    material: new PolylineDashMaterialProperty({ color: Color.fromCssColorString("#4fa3d9"), dashLength: 20 }),
  },
});

// Pedir al backend el área exacta con datos y ajustar la zona
async function loadCoverage(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/mission/coverage`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const c = (await response.json()) as { west: number; south: number; east: number; north: number };
    Object.assign(STUDY_ZONE, { west: c.west, south: c.south, east: c.east, north: c.north });
    zoneFill.rectangle!.coordinates = new ConstantProperty(Rectangle.fromDegrees(c.west, c.south, c.east, c.north));
    zoneBorder.polyline!.positions = new ConstantProperty(zoneOutline());
  } catch (error) {
    console.warn("Coverage unavailable, using the built-in study zone:", error);
  }
}
void loadCoverage();

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
  hideElevationProfile();
  document.querySelector<HTMLDivElement>("#site-photo")!.hidden = true;
  document.querySelector<HTMLButtonElement>("#traverse-button")!.disabled = true;
  const oldRoute = viewer.entities.getById("planned-route");
  if (oldRoute) oldRoute.show = false;
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
  if (animating) return;
    // Si hizo clic en la miniatura, abrir la foto grande en vez de mover al astronauta
  const pickedObject = viewer.scene.pick(click.position);
  if (pickedObject?.id === targetPhotoEntity && currentMission) {
    showSitePhoto(currentMission);
    return;
  }

  if (!viewer.scene.pickPositionSupported) return;
  const picked = viewer.scene.pickPosition(click.position);
    if (!picked) return;

  // ¿El punto está dentro de la zona de estudio?
  const carto = Cartographic.fromCartesian(picked);
  const lon = CesiumMath.toDegrees(carto.longitude);
  const lat = CesiumMath.toDegrees(carto.latitude);
  if (!isInsideZone(lon, lat)) {
    setResult(
      `⚠ OUTSIDE STUDY ZONE · That point (${lon.toFixed(3)}°, ${lat.toFixed(3)}°) is too far from the mission area. ` +
        `Place the astronaut inside the blue dashed zone.`,
      "error"
    );
    return; // el astronauta NO se mueve
  }
  placeAstronaut(picked);
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

function drawRoute(route: Coordinate[], isDemo: boolean, metrics?: RouteMetrics): void {
  const positions = route.map((p) => Cartesian3.fromDegrees(p.longitude, p.latitude));
  routeEntity.polyline!.positions = new ConstantProperty(positions);
  routeEntity.show = true;
  previewLine.show = false;

  // Distancia: la del planificador (terreno real) o, en DEMO, sumando cada tramo
  let distanceM = metrics?.distance_m ?? 0;
  if (!metrics) {
    for (let i = 1; i < route.length; i++) {
      distanceM += new EllipsoidGeodesic(
        Cartographic.fromDegrees(route[i - 1].longitude, route[i - 1].latitude),
        Cartographic.fromDegrees(route[i].longitude, route[i].latitude),
        Ellipsoid.MARS
      ).surfaceDistance;
    }
  }

  const km = distanceM / 1000;
  const oneWayH = metrics?.duration_s ? metrics.duration_s / 3600 : km / WALK_SPEED_KMH;
  const terrain = metrics
    ? ` · ↑ ${Math.round(metrics.ascent_m)} m ↓ ${Math.round(metrics.descent_m)} m · max slope ${metrics.max_slope_deg.toFixed(0)}°` +
      (metrics.max_slope_deg > 25 ? " ⚠ steep segment" : "")
    : "";
  const roundTripH = oneWayH * 2; // tiene que volver a la base con oxígeno
  const limit = currentMission?.evaMaxHours;
    const o2NeededH = roundTripH * o2Multiplier(missionLoadKg()); // con el peso del equipo
  const withinLimit = limit === undefined || o2NeededH <= limit;
  const returnHour = Number(evaStartSelect.value) + roundTripH;
  const afterDusk = returnHour > 18;

    setResult(
    (isDemo ? "DEMO ROUTE (planner offline) · " : "REAL TERRAIN ROUTE (USGS 1 m DEM) · ") +
      `Distance ${km.toFixed(2)} km${terrain} · One-way ≈ ${oneWayH.toFixed(1)} h · ` +
      `Round trip ≈ ${roundTripH.toFixed(1)} h · O₂ needed ≈ ${o2NeededH.toFixed(1)} h` +
      (limit !== undefined ? ` / EVA limit ${limit} h` : "") +
      (withinLimit ? "" : " · ⚠ NOT ENOUGH O₂") +
      (afterDusk
        ? ` · ⚠ Returns after dusk (~${Math.floor(returnHour % 24)}:00, air ≈ ${Math.round(airTempAt(returnHour))} °C)`
        : ""),
    isDemo || !withinLimit || afterDusk ? "warning" : "info"
  );
  // Encuadrar la ruta completa
  const sphere = BoundingSphere.fromPoints(
    route.map((p) => Cartesian3.fromDegrees(p.longitude, p.latitude, GALE_SURFACE_HEIGHT_M))
  );
  viewer.camera.flyToBoundingSphere(sphere, {
    offset: new HeadingPitchRange(0, CesiumMath.toRadians(-50), sphere.radius * 3),
    duration: 2,
  });
  
  prepareTraverse(route, oneWayH);
}




// ---------- Animación del recorrido ----------
const ANIMATION_SECONDS = 15; // duración real de la animación (el tiempo de misión se simula)
const traverseButton = document.querySelector<HTMLButtonElement>("#traverse-button")!;

let animating = false;
let traverse: { positions: Cartesian3[]; cumulative: number[]; totalM: number; oneWayH: number } | null = null;

// Guarda la ruta y la distancia acumulada en cada punto
function prepareTraverse(route: Coordinate[], oneWayH: number): void {
  const positions = route.map((p) => Cartesian3.fromDegrees(p.longitude, p.latitude));
  const cumulative = [0];
  for (let i = 1; i < route.length; i++) {
    const segment = new EllipsoidGeodesic(
      Cartographic.fromDegrees(route[i - 1].longitude, route[i - 1].latitude),
      Cartographic.fromDegrees(route[i].longitude, route[i].latitude),
      Ellipsoid.MARS
    ).surfaceDistance;
    cumulative.push(cumulative[i - 1] + segment);
  }
  traverse = { positions, cumulative, totalM: cumulative[cumulative.length - 1], oneWayH };
  traverseButton.disabled = false;
}

// Punto de la ruta a cierta distancia desde el inicio
function positionAtDistance(d: number): Cartesian3 {
  const { positions, cumulative } = traverse!;
  let i = 1;
  while (i < cumulative.length - 1 && cumulative[i] < d) i++;
  const segmentLength = cumulative[i] - cumulative[i - 1] || 1;
  const t = Math.min(Math.max((d - cumulative[i - 1]) / segmentLength, 0), 1);
  return Cartesian3.lerp(positions[i - 1], positions[i], t, new Cartesian3());
}

function startTraverse(): void {
  if (!traverse || animating) return;
  const { totalM, oneWayH } = traverse;
  const limit = currentMission?.evaMaxHours;

  // Punto de no retorno: con la mitad del oxígeno hay que volver a la base
   const turnaroundH = limit !== undefined ? limit / (2 * o2Multiplier(missionLoadKg())) : Infinity;
  const stopFraction = Math.min(1, turnaroundH / oneWayH);
  const mustTurnBack = stopFraction < 1;

  animating = true;
  traverseButton.disabled = true;
  planButton.disabled = true;

  const astronautPosition = new ConstantPositionProperty(traverse.positions[0]);
  astronautEntity.position = astronautPosition;

  const startTime = performance.now();
  const durationMs = ANIMATION_SECONDS * 1000 * stopFraction;

  function frame(now: number): void {
    const progress = Math.min((now - startTime) / durationMs, 1) * stopFraction;
    const point = positionAtDistance(progress * totalM);
    astronautPosition.setValue(point);

    const elapsedH = progress * oneWayH;
    renderTelemetry(telemetryAt(elapsedH, true));
    const oxygen = limit !== undefined ? ` · O₂ left ${(limit - elapsedH).toFixed(1)} h` : "";
    setResult(
      `TRAVERSING · ${((progress * totalM) / 1000).toFixed(2)} / ${(totalM / 1000).toFixed(2)} km` +
        ` · elapsed ${elapsedH.toFixed(1)} h${oxygen}`,
      "info"
    );

    if (progress < stopFraction) {
      requestAnimationFrame(frame);
    } else {
      finishTraverse(point, mustTurnBack, elapsedH);
    }
  }
  requestAnimationFrame(frame);
}

function finishTraverse(point: Cartesian3, turnedBack: boolean, elapsedH: number): void {
  renderTelemetry(telemetryAt(elapsedH, false));
  animating = false;
  planButton.disabled = false;

  // El astronauta queda donde terminó
  astronautCartesian = point;
  const carto = Cartographic.fromCartesian(point);
  startLonInput.value = CesiumMath.toDegrees(carto.longitude).toFixed(5);
  startLatInput.value = CesiumMath.toDegrees(carto.latitude).toFixed(5);

  if (turnedBack) {
    setResult(
      `⚠ TURNAROUND POINT · After ${elapsedH.toFixed(1)} h the astronaut must head back to keep ` +
        `enough oxygen for the return. Target not reached: choose a closer start or use rover support.`,
      "error"
    );
  } else {
    setResult(
      `✅ MISSION TARGET REACHED · ${currentMission?.name ?? "Target"} · ` +
        `${elapsedH.toFixed(1)} h of walking. Ready to start the science work.`,
      "info"
    );

    if (currentMission) showSitePhoto(currentMission);
  }
}

traverseButton.addEventListener("click", startTraverse);














// ---------- Foto real del lugar al llegar ----------
const sitePhoto = document.querySelector<HTMLDivElement>("#site-photo")!;
const sitePhotoImg = document.querySelector<HTMLImageElement>("#site-photo-img")!;
const sitePhotoCaption = document.querySelector<HTMLParagraphElement>("#site-photo-caption")!;
const sitePhotoCredit = document.querySelector<HTMLParagraphElement>("#site-photo-credit")!;

function showSitePhoto(mission: Mission): void {
  sitePhotoImg.src = mission.photo.src;
  sitePhotoImg.alt = mission.photo.caption;
  sitePhotoCaption.textContent = mission.photo.caption;
  sitePhotoCredit.textContent = `Image: ${mission.photo.credit}`;
  sitePhoto.hidden = false;
}

document.querySelector<HTMLButtonElement>("#site-photo-close")!
  .addEventListener("click", () => { sitePhoto.hidden = true; });







// ---------- Telemetría del traje ----------
const evaStartSelect = document.querySelector<HTMLSelectElement>("#eva-start")!;

interface Telemetry {
  o2LeftH: number;
  o2Pct: number;
  heartRate: number;
  batteryPct: number;
  airTempC: number;
  radiationMsv: number;
}

function missionLoadKg(): number {
  return currentMission ? currentMission.equipment.reduce((sum, e) => sum + e.massKg, 0) : 0;
}

function setRow(id: string, value: string, level?: Level): void {
  const row = document.querySelector<HTMLDivElement>(`#${id}`)!;
  row.querySelector("strong")!.textContent = value;
  if (level) row.dataset.level = level;
  else delete row.dataset.level;
}

function renderTelemetry(t: Telemetry): void {
  setRow("tm-o2", `${t.o2LeftH.toFixed(1)} h · ${Math.round(t.o2Pct)}%`, levelFromPercent(t.o2Pct));
  setRow("tm-hr", `${t.heartRate} bpm`, levelFromHeartRate(t.heartRate));
  setRow("tm-battery", `${Math.round(t.batteryPct)}%`, levelFromPercent(t.batteryPct));
  setRow("tm-air", `${Math.round(t.airTempC)} °C`, levelFromAirTemp(t.airTempC));
  setRow("tm-pressure", `${GALE_ENVIRONMENT.pressureMinPa}–${GALE_ENVIRONMENT.pressureMaxPa} Pa`);
  setRow("tm-radiation", `${t.radiationMsv.toFixed(3)} mSv`, "ok");
}

// Telemetría a cierta hora de la caminata (elapsedH = horas desde que salió)
function telemetryAt(elapsedH: number, walking: boolean): Telemetry {
  const limit = currentMission?.evaMaxHours ?? 6;
  const loadKg = missionLoadKg();
  const o2LeftH = Math.max(limit - elapsedH * o2Multiplier(loadKg), 0);
  const airTempC = airTempAt(Number(evaStartSelect.value) + elapsedH);
  return {
    o2LeftH,
    o2Pct: (o2LeftH / limit) * 100,
    heartRate: walking ? heartRateBpm(loadKg, 3 * Math.sin(elapsedH * 40)) : 72,
    batteryPct: Math.max(100 - elapsedH * batteryDrainPerHour(airTempC), 0),
    airTempC,
    radiationMsv: elapsedH * RADIATION_MSV_PER_HOUR,
  };
}

function resetTelemetry(): void {
  renderTelemetry(telemetryAt(0, false));
}

evaStartSelect.addEventListener("change", resetTelemetry);
resetTelemetry();

// ---------- Perfil de elevación de la ruta real ----------
// Basado en el gráfico de perfil de Steven (rama mapa-de-minerales-y-pendientes),
// ahora alimentado con elevation_profile del planificador A*.
type ElevationSample = GeoPlanResponse["elevation_profile"][number];

function slopeColor(deg: number): string {
  if (deg >= 20) return "#e46549"; // empinado
  if (deg >= 10) return "#e8bb69";
  if (deg >= 5) return "#65a39e";
  return "#7fb3d5"; // casi plano
}

function hideElevationProfile(): void {
  document.querySelector<HTMLDivElement>("#route-profile")!.hidden = true;
}

function showElevationProfile(samples: ElevationSample[], metrics: RouteMetrics): void {
  const box = document.querySelector<HTMLDivElement>("#route-profile")!;
  const canvas = document.querySelector<HTMLCanvasElement>("#profile-chart")!;
  const caption = document.querySelector<HTMLParagraphElement>("#profile-caption")!;
  const ctx = canvas.getContext("2d");
  if (!ctx || samples.length < 2) return;
  box.hidden = false;

  // Área de dibujo lógica 310x150 (el canvas es 2x para que se vea nítido)
  const W = 310, H = 150, left = 46, right = 8, top = 10, bottom = 22;
  const total = samples[samples.length - 1].distance_m || 1;
  const heights = samples.map((s) => s.elevation_m);
  const floor = Math.min(...heights);
  const range = Math.max(Math.max(...heights) - floor, 1);
  const x = (d: number) => left + (d / total) * (W - left - right);
  const y = (e: number) => top + (1 - (e - floor) / range) * (H - top - bottom);

  ctx.setTransform(2, 0, 0, 2, 0, 0);
  ctx.clearRect(0, 0, W, H);
  ctx.font = "10px system-ui";
  ctx.lineWidth = 1;

  // Líneas guía y etiquetas de elevación
  for (const e of [floor, floor + range / 2, floor + range]) {
    ctx.strokeStyle = "#2c3b48";
    ctx.beginPath();
    ctx.moveTo(left, y(e));
    ctx.lineTo(W - right, y(e));
    ctx.stroke();
    ctx.fillStyle = "#b6c3cd";
    ctx.textAlign = "right";
    ctx.fillText(`${Math.round(e)} m`, left - 4, y(e) + 3);
  }
  ctx.textAlign = "left";
  ctx.fillText("0 m", left, H - 6);
  ctx.textAlign = "right";
  ctx.fillText(`${(total / 1000).toFixed(2)} km`, W - right, H - 6);

  // Relleno bajo la curva
  ctx.beginPath();
  ctx.moveTo(x(0), y(floor));
  for (const s of samples) ctx.lineTo(x(s.distance_m), y(s.elevation_m));
  ctx.lineTo(x(total), y(floor));
  ctx.closePath();
  ctx.fillStyle = "rgba(240, 138, 75, 0.12)";
  ctx.fill();

  // Línea coloreada según la pendiente de cada tramo
  const step = Math.max(1, Math.floor(samples.length / 400));
  const indices: number[] = [];
  for (let i = 0; i < samples.length; i += step) indices.push(i);
  if (indices[indices.length - 1] !== samples.length - 1) indices.push(samples.length - 1);
  ctx.lineWidth = 2;
  for (let k = 1; k < indices.length; k++) {
    const a = samples[indices[k - 1]];
    const b = samples[indices[k]];
    ctx.strokeStyle = slopeColor(b.slope_deg);
    ctx.beginPath();
    ctx.moveTo(x(a.distance_m), y(a.elevation_m));
    ctx.lineTo(x(b.distance_m), y(b.elevation_m));
    ctx.stroke();
  }

  caption.textContent =
    `↑ ${Math.round(metrics.ascent_m)} m · ↓ ${Math.round(metrics.descent_m)} m · ` +
    `max slope ${metrics.max_slope_deg.toFixed(0)}° · mean ${metrics.mean_slope_deg.toFixed(1)}°`;
}

void checkApi();
