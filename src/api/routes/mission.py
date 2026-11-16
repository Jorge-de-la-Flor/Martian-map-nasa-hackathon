import mimetypes

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from math import isfinite
from core.config import get_settings
from geospatial.catalog import load_data_catalog
from geospatial.raster import (
    inspect_raster,
    resolve_data_path,
)
from geospatial.geo import load_georeference
from models.mission import (
    CoverageResponse,
    DataCatalogResponse,
    ElevationResponse,
    GeoPlanRequest,
    GeoPlanResponse,
    GeoRoutePoint,
    MissionInfo,
    PlanRequest,
    PlanResponse,
    ProjectedCoordinate,
    RasterInfo,
)
from services.astar import NoPathError, PlanningLimitError
from services.planner import RoutePlanner

router = APIRouter(
    prefix="/mission",
    tags=["mission"],
)

settings = get_settings()

planner = RoutePlanner(
    data_dir=settings.data_dir,
)


@router.get("", response_model=MissionInfo)
def mission_info() -> MissionInfo:
    try:
        catalog = load_data_catalog(settings.data_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    has_route_dem = any(layer.role == "route_dem" and layer.available for layer in catalog.layers)

    return MissionInfo(
        name="Mars Mission Planner",
        description=("Terrain-aware route planning using registered Martian geospatial datasets."),
        route_profiles=[
            "direct",
            "low_slope",
            "conservative",
        ],
        planning_status=("ready" if has_route_dem and catalog.region_name else "awaiting_data"),
        region_name=catalog.region_name,
    )


@router.get(
    "/layers",
    response_model=DataCatalogResponse,
)
def list_layers() -> DataCatalogResponse:
    try:
        return load_data_catalog(settings.data_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid data catalog: {exc}",
        ) from exc


@router.get("/layers/{layer_id}/file")
def get_layer_file(layer_id: str) -> FileResponse:
    try:
        catalog = load_data_catalog(settings.data_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    layer = next(
        (item for item in catalog.layers if item.id == layer_id),
        None,
    )

    if layer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer not found in the data catalog.",
        )

    if not layer.available or not layer.local_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer data is not available locally.",
        )

    try:
        path = resolve_data_path(
            settings.data_dir,
            layer.local_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    media_type, _ = mimetypes.guess_type(path.name)

    return FileResponse(
        path=path,
        media_type=media_type or "application/octet-stream",
    )


@router.get(
    "/raster",
    response_model=RasterInfo,
)
def raster_info(
    path: str = Query(
        ...,
        min_length=1,
        description="Raster path relative to the data directory.",
    ),
) -> RasterInfo:
    try:
        requested = resolve_data_path(
            settings.data_dir,
            path,
        )

        result = inspect_raster(requested)

        return RasterInfo(**result)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/elevation",
    response_model=ElevationResponse,
)
def elevation_at_point(
    dem_path: str = Query(..., min_length=1),
    x_m: float = Query(...),
    y_m: float = Query(...),
) -> ElevationResponse:
    try:
        return planner.query_elevation(
            dem_path=dem_path,
            x_m=x_m,
            y_m=y_m,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/plan",
    response_model=PlanResponse,
)
def plan_route(payload: PlanRequest) -> PlanResponse:
    try:
        return planner.plan(payload)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except NoPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except PlanningLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc



# ---------- Puente para el frontend: longitud/latitud ----------
def _route_dem() -> tuple[str, str | None]:
    """Devuelve el DEM de rutas registrado en el catálogo y el nombre de la región."""
    try:
        catalog = load_data_catalog(settings.data_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    layer = next(
        (
            item
            for item in catalog.layers
            if item.role == "route_dem" and item.available and item.local_path
        ),
        None,
    )

    if layer is None or layer.local_path is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No route DEM is available. Run scripts/prepare_boxwork_dem.py "
                "and register it in data/catalog.json."
            ),
        )

    return layer.local_path, catalog.region_name


def _load_route_georeference(dem_path: str):
    try:
        return load_georeference(resolve_data_path(settings.data_dir, dem_path))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/coverage",
    response_model=CoverageResponse,
)
def route_coverage() -> CoverageResponse:
    """Rectángulo (en grados) donde hay datos de elevación para planificar rutas."""
    dem_path, region_name = _route_dem()
    geo = _load_route_georeference(dem_path)

    return CoverageResponse(
        region_name=region_name,
        dem_path=dem_path,
        crs=geo.crs.to_string(),
        west=geo.west,
        south=geo.south,
        east=geo.east,
        north=geo.north,
    )


@router.post(
    "/plan/geo",
    response_model=GeoPlanResponse,
)
def plan_route_geo(payload: GeoPlanRequest) -> GeoPlanResponse:
    """Recibe longitud/latitud, usa el A* existente y devuelve la ruta también en longitud/latitud."""
    dem_path, _ = _route_dem()
    geo = _load_route_georeference(dem_path)

    start_x, start_y = geo.to_projected.transform(
        payload.start.longitude,
        payload.start.latitude,
    )
    end_x, end_y = geo.to_projected.transform(
        payload.destination.longitude,
        payload.destination.latitude,
    )

    if not all(isfinite(value) for value in (start_x, start_y, end_x, end_y)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The coordinates could not be converted to the DEM projection.",
        )

    # Reutiliza el endpoint original (mismo A*, mismos errores y mensajes)
    plan = plan_route(
        PlanRequest(
            dem_path=dem_path,
            start=ProjectedCoordinate(x_m=start_x, y_m=start_y),
            destination=ProjectedCoordinate(x_m=end_x, y_m=end_y),
            profile=payload.profile,
            max_slope_deg=payload.max_slope_deg,
            walking_speed_m_s=payload.walking_speed_m_s,
        )
    )

    lons, lats = geo.to_geographic.transform(
        [point.x_m for point in plan.route],
        [point.y_m for point in plan.route],
    )

    route_geo = [
        GeoRoutePoint(
            longitude=float(lon),
            latitude=float(lat),
            elevation_m=point.elevation_m,
            slope_deg=point.slope_deg,
        )
        for lon, lat, point in zip(lons, lats, plan.route)
    ]

    return GeoPlanResponse(**plan.model_dump(), route_geo=route_geo)