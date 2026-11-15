import {
  BoundingSphere, Cartesian2, Cartesian3, Color, ConstantProperty, HeadingPitchRange,
  ClassificationType, GeographicTilingScheme, HeightReference, HorizontalOrigin,
  ImageryLayer, Rectangle, UrlTemplateImageryProvider,
  type Cesium3DTileset, type Entity, type Viewer,
} from "cesium";
import type { Coordinate } from "./missions";
import { MARS_REFERENCE } from "./mars-coordinates";

interface Site extends Coordinate {
  name: string;
  landform: string;
  waypoint_sol: number;
  reported_sample_minerals: string;
  science_source: string;
}

interface Profile {
  distance_m: number;
  ascent_m: number | null;
  descent_m: number | null;
  samples: { distance_m: number; elevation_m: number | null }[];
}

interface BoxworkAnalysis {
  sites: Site[];
  slope: {
    bounds_mars_degrees: { west: number; south: number; east: number; north: number };
    legend: { label: string; color: string }[];
  };
  dem_source: string;
  dem_credit: string;
  waypoint_credit: string;
  mineralogy_source: string;
  profile: Profile;
}

const meters = (value: number | null) => value === null ? "—" : value.toFixed(2) + " m";

function drawProfile(canvas: HTMLCanvasElement, profile: Profile): void {
  const context = canvas.getContext("2d");
  const heights = profile.samples.flatMap(({ elevation_m }) => elevation_m === null ? [] : [elevation_m]);
  if (!context || heights.length === 0) return;

  const floor = Math.min(...heights);
  const range = Math.max(Math.max(...heights) - floor, 0.1);
  const x = (distance: number) => 66 + distance / profile.distance_m * 227;
  const y = (elevation: number) => 113 - (elevation - floor) / range * 95;
  context.setTransform(2, 0, 0, 2, 0, 0);
  context.clearRect(0, 0, 310, 140);
  context.font = "11px system-ui";
  context.fillStyle = "#b6c3cd";
  context.strokeStyle = "#435565";
  for (const elevation of [floor, floor + range / 2, floor + range]) {
    context.beginPath();
    context.moveTo(x(0), y(elevation));
    context.lineTo(x(profile.distance_m), y(elevation));
    context.stroke();
    context.fillText(elevation.toFixed(1) + " m", 1, y(elevation) + 4);
  }
  context.fillText("0 m", x(0), 133);
  context.textAlign = "right";
  context.fillText(meters(profile.distance_m), x(profile.distance_m), 133);
  context.strokeStyle = "#ffb28a";
  context.lineWidth = 2;
  context.beginPath();
  let previousSampleWasValid = false;
  for (const { distance_m, elevation_m } of profile.samples) {
    if (elevation_m === null) {
      previousSampleWasValid = false;
      continue;
    }
    if (previousSampleWasValid) context.lineTo(x(distance_m), y(elevation_m));
    else context.moveTo(x(distance_m), y(elevation_m));
    previousSampleWasValid = true;
  }
  context.stroke();
}

export function createBoxworkPanel(
  viewer: Viewer,
  panel: HTMLElement,
  apiBase: string,
  marsReady: Promise<Cesium3DTileset | undefined>,
  onDestination: (site: Site) => void,
) {
  const api = apiBase + "/api/mission/boxwork";
  panel.innerHTML = `
    <h3>Mount Sharp · Boxwork</h3>
    <p class="boxwork-status" role="status"></p>
    <div class="boxwork-data" hidden>
      <div class="boxwork-controls">
        <button type="button" class="boxwork-focus" disabled>Focus study area</button>
        <label><input type="checkbox" class="boxwork-slope" disabled> Show slope</label>
      </div>
      <ul class="boxwork-legend" aria-label="Slope in degrees" hidden></ul>
      <div class="boxwork-sites" aria-label="Curiosity reference stops"></div>
      <p class="boxwork-site-detail" aria-live="polite"></p>
      <a class="boxwork-site-source terrain-link">NASA observation</a>
      <span aria-hidden="true"> · </span>
      <a class="boxwork-mineralogy terrain-link">JPL sample results</a>
      <h4>Reference elevation profile</h4>
      <canvas class="boxwork-chart" width="620" height="280" role="img"
        aria-label="DEM elevation along the straight transect between rover positions"></canvas>
      <p class="boxwork-metrics"></p>
      <a class="boxwork-dem-source terrain-link">USGS elevation model</a>
    </div>
  `;

  const status = panel.querySelector<HTMLParagraphElement>(".boxwork-status")!;
  const content = panel.querySelector<HTMLElement>(".boxwork-data")!;
  const focus = panel.querySelector<HTMLButtonElement>(".boxwork-focus")!;
  const toggle = panel.querySelector<HTMLInputElement>(".boxwork-slope")!;
  const legend = panel.querySelector<HTMLUListElement>(".boxwork-legend")!;
  const sites = panel.querySelector<HTMLElement>(".boxwork-sites")!;
  const detail = panel.querySelector<HTMLParagraphElement>(".boxwork-site-detail")!;
  const siteSource = panel.querySelector<HTMLAnchorElement>(".boxwork-site-source")!;
  const mineralogy = panel.querySelector<HTMLAnchorElement>(".boxwork-mineralogy")!;
  const demSource = panel.querySelector<HTMLAnchorElement>(".boxwork-dem-source")!;
  const chart = panel.querySelector<HTMLCanvasElement>(".boxwork-chart")!;
  const metrics = panel.querySelector<HTMLParagraphElement>(".boxwork-metrics")!;

  let active = false;
  let analysis: Promise<BoxworkAnalysis> | undefined;
  let rectangle: Rectangle;
  let siteButtons: HTMLButtonElement[] = [];
  let markers: Entity[] = [];
  let transect: Entity;
  let layer: ImageryLayer | undefined;
  let loadingLayer: Promise<void> | undefined;
  let dataset: BoxworkAnalysis;

  function selectSite(index: number): void {
    const site = dataset.sites[index];
    siteButtons.forEach((button, i) => button.setAttribute("aria-pressed", String(i === index)));
    markers.forEach((marker, i) => {
      marker.point!.color = new ConstantProperty(i === index ? Color.fromCssColorString("#ffad83") : Color.WHITE);
    });
    detail.textContent = site.landform + " · " + site.reported_sample_minerals
      + " · rover position, sol " + site.waypoint_sol + " · " + dataset.waypoint_credit;
    siteSource.href = site.science_source;
    onDestination(site);
  }

  function focusArea(): void {
    const profile = dataset.profile;
    const points = dataset.sites.map((site, index) => Cartesian3.fromDegrees(site.longitude, site.latitude,
      (index === 0 ? profile.samples[0] : profile.samples.at(-1))?.elevation_m ?? 0));
    const area = BoundingSphere.fromPoints(points);
    area.radius = Math.max(area.radius, Cartesian3.distance(
      Cartesian3.fromRadians(rectangle.west, rectangle.south),
      Cartesian3.fromRadians(rectangle.east, rectangle.north),
    ) / 2);
    viewer.camera.flyToBoundingSphere(area, {
      offset: new HeadingPitchRange(0, -Math.PI / 2, area.radius * 2.9),
      duration: 1.25,
    });
  }

  function configure(data: BoxworkAnalysis): BoxworkAnalysis {
    dataset = data;
    const { west, south, east, north } = data.slope.bounds_mars_degrees;
    rectangle = Rectangle.fromDegrees(west, south, east, north);
    markers = data.sites.map((site) => viewer.entities.add({
      name: site.name,
      position: Cartesian3.fromDegrees(site.longitude, site.latitude, 3),
      show: false,
      point: {
        pixelSize: 11, color: Color.WHITE, outlineColor: Color.BLACK, outlineWidth: 2,
        heightReference: HeightReference.RELATIVE_TO_3D_TILE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: site.name, font: "13px sans-serif", showBackground: true,
        heightReference: HeightReference.RELATIVE_TO_3D_TILE,
        pixelOffset: new Cartesian2(14, site.landform === "ridge" ? 16 : -16),
        horizontalOrigin: HorizontalOrigin.LEFT,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    }));
    transect = viewer.entities.add({
      name: "DEM reference transect",
      show: false,
      polyline: {
        positions: data.sites.map((site) => Cartesian3.fromDegrees(site.longitude, site.latitude)),
        width: 3,
        clampToGround: true,
        classificationType: ClassificationType.CESIUM_3D_TILE,
        material: Color.WHITE,
      },
    });
    siteButtons = data.sites.map((site, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = site.name;
      button.onclick = () => selectSite(index);
      sites.append(button);
      return button;
    });
    for (const item of data.slope.legend) {
      const entry = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.style.backgroundColor = item.color;
      entry.append(swatch, item.label);
      legend.append(entry);
    }
    demSource.href = data.dem_source;
    demSource.title = data.dem_credit;
    mineralogy.href = data.mineralogy_source;
    const profile = data.profile;
    metrics.textContent = meters(profile.distance_m) + " · ascent " + meters(profile.ascent_m)
      + " · descent " + meters(profile.descent_m);
    drawProfile(chart, profile);
    return data;
  }

  function updateLayerVisibility(): void {
    if (layer) layer.show = active && toggle.checked;
    legend.hidden = !layer?.show;
  }

  focus.onclick = focusArea;
  toggle.onchange = () => {
    updateLayerVisibility();
    if (!toggle.checked || layer || loadingLayer) return;
    status.textContent = "Loading slope layer…";
    loadingLayer = marsReady.then((tileset) => {
      if (!tileset) throw new Error("Cesium Mars is unavailable.");
      const provider = new UrlTemplateImageryProvider({
        url: api + "/slope.png",
        rectangle,
        credit: dataset.dem_credit,
        tilingScheme: new GeographicTilingScheme({
          rectangle, ellipsoid: MARS_REFERENCE, numberOfLevelZeroTilesX: 1, numberOfLevelZeroTilesY: 1,
        }),
        // The 3D Tiles draper in Cesium 1.147 treats maximumLevel as exclusive.
        maximumLevel: 1,
      });
      const slopeLayer = new ImageryLayer(provider, { rectangle, alpha: 0.65 });
      tileset.imageryLayers.add(slopeLayer);
      layer = slopeLayer;
      provider.errorEvent.addEventListener(() => {
        if (layer !== slopeLayer) return;
        toggle.checked = false;
        if (tileset.imageryLayers.contains(slopeLayer)) tileset.imageryLayers.remove(slopeLayer);
        layer = undefined;
        updateLayerVisibility();
        status.textContent = "Slope image unavailable. Use the 2D terrain analysis or retry.";
      });
      updateLayerVisibility();
      status.textContent = "";
    }).catch(() => {
      toggle.checked = false;
      status.textContent = "Slope layer unavailable. Use the 2D terrain analysis or retry.";
    }).finally(() => { loadingLayer = undefined; });
  };

  let activation = 0;
  async function setActive(visible: boolean): Promise<void> {
    const current = ++activation;
    active = visible;
    panel.hidden = !visible;
    markers.forEach((marker) => { marker.show = false; });
    if (transect) transect.show = false;
    updateLayerVisibility();
    if (!visible) return;
    status.textContent = "Loading Curiosity stops and elevation profile…";
    analysis ??= fetch(api + "/analysis").then(async (response) => {
      if (!response.ok) throw new Error("Boxwork data are unavailable.");
      return configure(await response.json() as BoxworkAnalysis);
    });
    try {
      await analysis;
    } catch {
      analysis = undefined;
      if (current === activation) {
        status.textContent = "Boxwork data unavailable. Start the local API and reselect the mission.";
      }
      return;
    }
    if (current !== activation) return;
    content.hidden = false;
    selectSite(0);
    status.textContent = "";
    const tileset = await marsReady;
    if (current !== activation) return;
    markers.forEach((marker) => { marker.show = Boolean(tileset); });
    transect.show = Boolean(tileset);
    toggle.disabled = !tileset;
    focus.disabled = !tileset;
    if (tileset) focusArea();
    else status.textContent = "Cesium Mars is unavailable. The stop details and profile are still available.";
  }

  function selectPicked(entity: unknown): boolean {
    if (!active) return false;
    if (transect && entity === transect) return true;
    const selected = markers.findIndex((marker) => marker === entity);
    if (selected === -1) return false;
    selectSite(selected);
    return true;
  }

  return { setActive, selectPicked };
}
