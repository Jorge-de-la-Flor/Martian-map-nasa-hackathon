import { Ellipsoid } from "cesium";

// The rover catalog and the Gale raster use planetocentric latitude.
const marsRadius = 3_396_190;
export const MARS_REFERENCE = new Ellipsoid(marsRadius, marsRadius, marsRadius);
