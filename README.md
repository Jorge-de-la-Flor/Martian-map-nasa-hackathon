
# Mars Mission Planner

**From NASA Science Data to Human Exploration.**

Mars Mission Planner is a geospatial backend for exploring Martian terrain
and comparing candidate human-exploration routes using topographic costs.

## Current implementation

The Python backend provides:

- FastAPI application and mission endpoints.
- GeoTIFF inspection and single-band DEM loading.
- Validation of projected Martian coordinate systems.
- NoData and raster-boundary handling.
- Horn 3x3 terrain-slope calculation.
- Eight-connected A* pathfinding.
- Direct, Low Slope, and Conservative route profiles.
- Optional hazard, uncertainty, and blocked-area rasters.
- Distance, elevation-change, slope, hazard-exposure, and uncertainty metrics.
- A scientific data-source catalog.

The repository also contains a synthetic demonstration generator.
Synthetic data are used exclusively for software validation and are not
NASA observations.

## Technology

- Python 3.14
- FastAPI
- NumPy
- Rasterio
- PyProj / PROJ
- Pydantic
- uv
- pytest
- Ruff

The frontend is maintained separately from this backend.

## Requirements

- Python 3.14.x
- uv

No Node.js or npm installation is required to work on the Python backend.

## Installation

From the repository root:

```bash
uv lock
uv sync --group dev
```

## Validation

Run the test suite:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check .
```

Optional coverage report:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

## Synthetic demonstration

Generate a small synthetic Martian terrain:

```bash
uv run python scripts/create_synthetic_demo.py
```

This creates:

```text
data/
└── demo/
    ├── synthetic_dem.tif
    ├── synthetic_hazard.tif
    └── synthetic_uncertainty.tif
```

Start the API:

```bash
uv run uvicorn main:app --app-dir src --reload
```

Open:

- API root: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health
- Mission: http://127.0.0.1:8000/api/mission
- Data layers: http://127.0.0.1:8000/api/mission/layers

## Route-planning example

The synthetic generator prints suitable start and destination coordinates.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/mission/plan \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

The speed in this example is only an illustrative user assumption. It is not
a validated universal Mars walking speed.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API information |
| GET | `/api/health` | Health status |
| GET | `/api/mission` | Mission and planning status |
| GET | `/api/mission/layers` | Scientific data catalog |
| GET | `/api/mission/raster` | Raster metadata |
| GET | `/api/mission/elevation` | Elevation and slope at a point |
| POST | `/api/mission/plan` | Calculate a route |

## Coordinate requirements

The planner accepts x/y coordinates in metres in the active DEM's projected
Martian coordinate reference system.

The system does not interpret longitude and latitude as Earth coordinates.

A valid route DEM must declare:

- A projected CRS.
- Horizontal axes in metres.
- An ellipsoid with a semi-major axis compatible with Mars.
- A valid geotransform.
- A single elevation band.

The data-preparation process must preserve the source coordinate conventions,
planetary datum, units, and NoData semantics.

## Auxiliary layers

Optional route-planning rasters:

- Hazard: normalized values from 0 to 1.
- Uncertainty: normalized values from 0 to 1.
- Blocked: normalized values where values greater than or equal to 0.5
  represent blocked cells.

These layers must have identical dimensions, CRS, and pixel alignment
to the selected DEM. Misaligned layers are rejected rather than silently
resampled.

Optical and thermal context layers are registered separately in
`data/catalog.json`.

## Scientific data status

The initial catalog identifies candidate sources:

- CTX stereo DTM: route-scale topography, when coverage is available.
- MOLA MEGDR: regional topographic context.
- CTX global mosaic: optical context.
- THEMIS infrared mosaic: thermal context.

A source being listed in the catalog does not mean its data have been
downloaded or validated.

The study region remains pending until the team selects a region and
registers compatible local products.

## Scientific limitations

The route planner estimates terrain difficulty using available raster data.
It does not certify that a route is safe or physically traversable.

Orbital products may not resolve small rocks, loose sand, local hazards,
or recent surface changes.

Route-cost weights are model parameters. They are not universal physical
constants or validated human-mobility limits.
