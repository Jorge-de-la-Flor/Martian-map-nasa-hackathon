import {
  GeographicTilingScheme, ImageryLayer, Rectangle, SingleTileImageryProvider,
  UrlTemplateImageryProvider, type Viewer,
} from "cesium";
import { MARS_REFERENCE } from "./mars-coordinates";

const MARS_TREK = "https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0"
  + "/default/default028mm/{z}/{y}/{x}.png";
const GALE_CTX = Rectangle.fromDegrees(135.1842593, -6.5732988, 139.2413012, -2.8077809);
const MOSAIC_CREDIT = "Parker and Calef III, NASA/JPL and USGS Astrogeology";
const CTX_CREDIT = "NASA/JPL Mars Trek · MRO CTX Gale mosaic";

export interface Extent {
  west: number;
  south: number;
  east: number;
  north: number;
}

export async function addGaleImagery(
  viewer: Viewer, apiBase: string, onStatus: (text: string) => void,
): Promise<void> {
  const layers = viewer.imageryLayers;
  const trek = new UrlTemplateImageryProvider({
    url: MARS_TREK,
    tilingScheme: new GeographicTilingScheme({ ellipsoid: MARS_REFERENCE }),
    rectangle: GALE_CTX,
    maximumLevel: 12,
    credit: CTX_CREDIT,
  });
  layers.add(new ImageryLayer(trek, { rectangle: GALE_CTX }));
  onStatus("NASA/JPL Mars Trek · Gale CTX");

  const endpoint = apiBase + "/api/mission/boxwork";
  try {
    const response = await fetch(endpoint + "/imagery");
    if (!response.ok) return;
    const extents = await response.json() as Record<"gale-context" | "gale" | "mount-sharp", Extent>;
    const layersToAdd = await Promise.allSettled(Object.entries(extents).map(async ([name, bounds]) => {
      const rectangle = Rectangle.fromDegrees(bounds.west, bounds.south, bounds.east, bounds.north);
      const provider = await SingleTileImageryProvider.fromUrl(endpoint + "/" + name + ".png", {
        rectangle, ellipsoid: MARS_REFERENCE,
        credit: name === "gale-context" ? CTX_CREDIT : MOSAIC_CREDIT,
      });
      return new ImageryLayer(provider, { rectangle });
    }));
    let index = 1;
    for (const result of layersToAdd) {
      if (result.status !== "fulfilled") continue;
      layers.add(result.value, index++);
    }
    if (index > 1) onStatus("NASA/JPL Mars Trek · USGS Gale imagery");
  } catch {
    // The public CTX layer also works without the locally prepared imagery.
  }
}
