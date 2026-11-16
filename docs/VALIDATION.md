# Validation plan

## Software validation

The automated test suite uses synthetic georeferenced rasters.

| Test | Expected result |
|---|---|
| Flat DEM | Slope is approximately zero |
| Synthetic ramp | Slope matches analytical gradient |
| NoData neighborhood | Slope is unavailable |
| Direct route | A* finds a feasible shortest-distance route |
| Blocked corners | A* does not move diagonally through blocked corners |
| Identical cells | Planning is rejected |
| NoData barrier | No route crosses missing elevation coverage |
| Hazard corridor | Conservative can avoid a localized high-hazard area |
| Misaligned layer | Auxiliary raster is rejected |
| Elevation query | Returns the selected DEM elevation |
| API plan | Returns route geometry and metrics |
| File traversal | Paths outside the data directory are rejected |

## Scientific validation

Software tests do not replace validation using original Martian products.

Before claiming a region is ready, the team must:

- Select one study region.
- Record the original source products and product identifiers.
- Verify coverage and resolution.
- Verify the planetary coordinate conventions.
- Verify the projected CRS and ellipsoid.
- Confirm that aligned layers represent the same geographic area.
- Check NoData and resampling behavior.
- Compare selected elevation samples against source-product values.
- Inspect slope and route outputs against known terrain features.
- Document product-specific uncertainties.

## Current status

The software test suite validates synthetic data behavior.

It does not yet validate the route planner against a real NASA DEM.

The local data directory must contain the selected regional products before
the application can be described as scientifically integrated.
