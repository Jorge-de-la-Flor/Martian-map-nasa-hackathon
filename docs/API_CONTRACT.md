# Backend API contract

Base URL:

`http://127.0.0.1:8000`

## Mission metadata

`GET /api/mission`

Returns mission metadata, selected region, and whether the route DEM
has been registered locally.

## Scientific layers

`GET /api/mission/layers`

Returns:

- Layer identifiers.
- Scientific category.
- Mission and instrument.
- Original source URL.
- Intended role.
- Nominal resolution.
- Local-file availability.

A listed source is not necessarily a downloaded or validated product.

## Raster metadata

`GET /api/mission/raster?path=dem.tif`

The path is relative to the configured data directory.

## Elevation query

`GET /api/mission/elevation?dem_path=dem.tif&x_m=0&y_m=0`

Returns:

- Projected coordinate.
- Raster row and column.
- Elevation in metres.
- Slope in degrees, if available.
- Active raster CRS.

## Route planning

`POST /api/mission/plan`

Example:

```json
{
  "dem_path": "demo/synthetic_dem.tif",
  "hazard_path": "demo/synthetic_hazard.tif",
  "uncertainty_path": "demo/synthetic_uncertainty.tif",
  "start": {
    "x_m": -4000,
    "y_m": 0
  },
  "destination": {
    "x_m": 4000,
    "y_m": 0
  },
  "profile": "conservative",
  "walking_speed_m_s": 0.5
}
```

Profiles:

- `direct`
- `low_slope`
- `conservative`

All input coordinates must be expressed in the projected CRS of the selected DEM.

## Route response

The response contains:

- Route points in projected metres.
- Elevation and slope for returned route points.
- Topographic elevation profile.
- Distance and accumulated elevation change.
- Maximum and distance-weighted mean slope.
- Estimated model cost.
- Hazard and uncertainty exposure distances.
- Number of A* expanded nodes.
- Scientific and model limitations.

The displayed route geometry can be downsampled for large paths.
All metrics are calculated from the complete internal path.
