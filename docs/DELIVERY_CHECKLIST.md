# Delivery checklist

## Backend software

- [ ] Dependencies resolve with uv.
- [ ] Ruff reports no errors.
- [ ] Unit tests pass.
- [ ] API integration tests pass.
- [ ] Synthetic demo runs.
- [ ] Swagger documentation is accessible.
- [ ] API contracts are shared with the frontend team.

## Geospatial and mathematical validation

- [ ] Flat surface produces approximately zero slope.
- [ ] Synthetic ramp matches analytical slope.
- [ ] NoData areas are not traversable.
- [ ] DEM CRS is projected and uses metres.
- [ ] Mars-compatible ellipsoid is confirmed.
- [ ] Auxiliary rasters match the DEM grid.
- [ ] A* avoids blocked cells and corners.
- [ ] All three profiles return valid routes where a path exists.
- [ ] Route metrics match independent calculations.

## Scientific integration

- [ ] Study region selected by the team.
- [ ] Route DEM acquired.
- [ ] Optical product acquired.
- [ ] Thermal product acquired.
- [ ] Original product identifiers documented.
- [ ] Coverage and resolution checked.
- [ ] Planetary coordinate conventions confirmed.
- [ ] Layers spatially aligned or their separate grids documented.
- [ ] At least three scientific categories available to the application.
- [ ] Results checked against original source products.

## Project delivery

- [ ] README updated.
- [ ] Data sources documented.
- [ ] Algorithm documented.
- [ ] Limitations visible.
- [ ] Backend changes merged into develop.
- [ ] Integrated application demonstrated.
