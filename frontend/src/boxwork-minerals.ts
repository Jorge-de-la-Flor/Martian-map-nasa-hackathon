import { sampleColors, type BoxworkAnalysis } from "./boxwork";
import boxworkImageryUrl from "./assets/boxwork-hirise.png";
import type { Coordinate } from "./missions";

// Bounds of the packaged mount-sharp.png crop recorded by build_gale_imagery.py.
const imageBounds = {
  west: 137.37845725485528,
  south: -4.8105517516624055,
  east: 137.38356904812727,
  north: -4.805304993551532,
};

export function createMineralView(panel: HTMLElement) {
  panel.innerHTML = `
    <figure class="mineral-map">
      <div class="mineral-map-image">
        <canvas width="800" height="420" role="img" aria-label="Curiosity sample locations"></canvas>
        <span class="mineral-north" aria-hidden="true">↑ N</span>
        <span class="mineral-route-key" hidden>Planned route</span>
        <div class="mineral-map-annotations" aria-hidden="true"></div>
      </div>
      <figcaption class="mineral-imagery"></figcaption>
    </figure>
    <ol class="mineral-samples"></ol>
    <div class="mineral-evidence">
      <p>Colors mark Curiosity’s sampling sites.</p>
      <a class="mineral-source">NASA/JPL results ↗</a>
    </div>
  `;

  const canvas = panel.querySelector("canvas")!;
  const context = canvas.getContext("2d")!;
  const credit = panel.querySelector<HTMLElement>(".mineral-imagery")!;
  const routeKey = panel.querySelector<HTMLElement>(".mineral-route-key")!;
  const annotations = panel.querySelector<HTMLElement>(".mineral-map-annotations")!;
  const samples = panel.querySelector<HTMLOListElement>(".mineral-samples")!;
  const source = panel.querySelector<HTMLAnchorElement>(".mineral-source")!;
  const photo = new Image();
  let analysis: BoxworkAnalysis | undefined;
  let route: Coordinate[] = [];
  let mapLabels: HTMLElement[] = [];

  function draw(): void {
    if (!analysis || panel.hidden) return;
    const bounds = imageBounds;
    const normalize = (point: Coordinate) => ({
      x: (point.longitude - bounds.west) / (bounds.east - bounds.west),
      y: (bounds.north - point.latitude) / (bounds.north - bounds.south),
    });
    let minX = 1, maxX = 0, minY = 1, maxY = 0;
    for (const point of [...analysis.sites, ...route]) {
      const { x, y } = normalize(point);
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
    const { width, height } = canvas;
    const extentAspect = (bounds.east - bounds.west) / (bounds.north - bounds.south);
    const cropAspect = width / height / extentAspect;
    const cropWidth = Math.max(0.26, maxX - minX + 0.16, (maxY - minY + 0.15) * cropAspect);
    const cropHeight = cropWidth / cropAspect;
    const left = Math.max(0, Math.min(1 - cropWidth, (minX + maxX - cropWidth) / 2));
    const top = Math.max(0, Math.min(1 - cropHeight, (minY + maxY - cropHeight) / 2));
    const project = (point: Coordinate) => {
      const { x, y } = normalize(point);
      return { x: (x - left) * width / cropWidth, y: (y - top) * height / cropHeight };
    };

    context.fillStyle = "#1c252b";
    context.fillRect(0, 0, width, height);
    if (photo.complete && photo.naturalWidth) {
      context.drawImage(
        photo, -left * width / cropWidth, -top * height / cropHeight,
        width / cropWidth, height / cropHeight,
      );
      credit.textContent = "HiRISE imagery · Parker and Calef III, NASA/JPL and USGS";
    } else {
      credit.textContent = "Sample locations · NASA/JPL-Caltech";
    }

    const path = route.map(project);
    routeKey.hidden = path.length < 2;
    canvas.setAttribute("aria-label", path.length > 1
      ? "Map of Curiosity sample locations and the planned route"
      : "Map of Curiosity sample locations");
    if (path.length > 1) {
      context.beginPath();
      context.moveTo(path[0].x, path[0].y);
      for (const { x, y } of path.slice(1)) context.lineTo(x, y);
      context.lineJoin = "round";
      context.lineCap = "round";
      context.strokeStyle = "#191715";
      context.lineWidth = 9;
      context.stroke();
      context.strokeStyle = "#fff8e9";
      context.lineWidth = 4;
      context.stroke();
    }

    analysis.sites.forEach((site, index) => {
      const { x, y } = project(site);
      const direction = site.landform === "hollow" ? -1 : 1;
      const labelX = Math.min(width * 0.78, Math.max(width * 0.22, x + direction * width * 0.16));
      const labelY = Math.min(height * 0.79, Math.max(height * 0.18, y + direction * 64));
      const color = sampleColors[site.landform];
      mapLabels[index].style.left = `${labelX / width * 100}%`;
      mapLabels[index].style.top = `${labelY / height * 100}%`;
      context.beginPath();
      context.moveTo(x, y);
      context.lineTo(labelX, labelY);
      context.lineWidth = 5;
      context.strokeStyle = "#191715";
      context.stroke();
      context.lineWidth = 2.5;
      context.strokeStyle = color;
      context.stroke();
      context.beginPath();
      context.arc(x, y, 15, 0, Math.PI * 2);
      context.fillStyle = color + "40";
      context.fill();
      context.beginPath();
      context.arc(x, y, 7, 0, Math.PI * 2);
      context.fillStyle = color;
      context.fill();
      context.strokeStyle = "#171510";
      context.lineWidth = 3;
      context.stroke();
    });
  }

  photo.onload = draw;

  function setSamples(data: BoxworkAnalysis): void {
    analysis = data;
    if (!photo.src) photo.src = boxworkImageryUrl;
    source.href = data.mineralogy_source;
    mapLabels = data.sites.map((site) => {
      const label = document.createElement("span");
      label.className = "mineral-map-label";
      label.style.setProperty("--sample-color", sampleColors[site.landform]);
      label.textContent = site.name;
      return label;
    });
    annotations.replaceChildren(...mapLabels);
    samples.replaceChildren(...data.sites.map((site) => {
      const item = document.createElement("li");
      item.style.setProperty("--sample-color", sampleColors[site.landform]);
      const label = document.createElement("strong");
      label.textContent = site.reported_sample_minerals;
      const location = document.createElement("a");
      location.href = site.science_source;
      location.textContent = site.name;
      const landform = document.createElement("span");
      landform.className = "mineral-landform";
      landform.textContent = site.landform === "hollow" ? "Hollow sample" : "Ridge sample";
      item.append(label, location, landform);
      return item;
    }));
    draw();
  }

  function setRoute(path: Coordinate[]): void {
    route = path;
    draw();
  }

  return { setSamples, setRoute, draw };
}
