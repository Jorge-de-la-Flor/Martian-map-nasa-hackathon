# Martian Map

Mars exploration viewer and terrain-aware route-planning MVP.

## Stack
- Backend: FastAPI, Rasterio, NumPy, PyProj, Shapely
- Frontend: Vite, TypeScript, CesiumJS
- Tooling: uv, pytest, Ruff

## Requirements
Python 3.14 (as configured), Node.js 20+, and uv.

## Backend
From the repository root:

```bash
uv sync --group dev
uv run uvicorn main:app --app-dir src --reload
```

Endpoints: `GET /`, `GET /api/health`, `GET /api/mission`,
`GET /api/mission/raster?path=...`, and `POST /api/mission/plan`.

The route planner estimates paths inside the local Mount Sharp DEM. The map
opens in 2D with public NASA Mars Trek imagery. See the Boxwork data guide for
the optional local imagery and route coverage.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal. Set `VITE_API_BASE_URL` in
`frontend/.env` if the API is not at `http://127.0.0.1:8000`.

## Raster inspection
Place a raster under `data/`. The API only accepts files inside the configured data
directory. Inspection reports metadata; it does not assume a raster is a Mars dataset.

See [Mount Sharp boxwork data](docs/mount-sharp-boxwork.md) for two Curiosity
reference waypoints, instructions to extract the local Gale elevation grid, and a
web preview of the slope map and reference elevation profile.

## Scientific limitation
A DEM-derived route is not a guarantee of traversability or safety. Orbital elevation
products may not resolve small rocks, loose sand, local hazards, or recent surface changes.

## Next milestones
1. Select one Mars study area and document authoritative DEM/imagery sources.
2. Add reproducible data preparation and coordinate-transform tests.
3. Implement and validate a grid-based route planner against known test rasters.
4. Render Mars-specific imagery/terrain in Cesium and display route/elevation profiles.
