# Local scientific data

Store regional scientific products in this directory.

The `catalog.json` file records candidate NASA data sources and their
local paths.

Large scientific data products should not be committed to Git without
an explicit decision by the team. Use the project's data-sharing
arrangement and document exact product identifiers and download sources.

## Expected product roles

- Route DEM: CTX stereo DTM or HiRISE DTM, if suitable local coverage exists.
- Regional topography: MOLA MEGDR.
- Optical context: CTX or HiRISE image product.
- Thermal context: THEMIS infrared product.
- Optional layers: spectral, radiation, atmospheric, or chemical observations.

## Planner raster requirements

The route DEM must be a single-band GeoTIFF using:

- A projected Mars CRS.
- Metre units on horizontal axes.
- A Mars-compatible ellipsoid.
- Explicit NoData.
- A valid affine transform.

Hazard, uncertainty, and blocked-area rasters must match the DEM in:

- Width and height.
- CRS.
- Affine transform.
- Pixel alignment.

Hazard and uncertainty values must be normalized from 0 to 1.
Blocked values at or above 0.5 are treated as obstacles.

Optical and thermal products may retain their own resolutions and
georeferencing in the scientific catalog, but they must not be treated
as the route DEM.

## Synthetic demonstration

The synthetic demonstration generator writes to `data/demo/`.
Those rasters are artificial and must never be cited as NASA observations.
