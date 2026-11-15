import mimetypes

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from core.config import get_settings
from geospatial.catalog import load_data_catalog
from geospatial.raster import (
    inspect_raster,
    resolve_data_path,
)
from models.mission import (
    DataCatalogResponse,
    ElevationResponse,
    MissionInfo,
    PlanRequest,
    PlanResponse,
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
