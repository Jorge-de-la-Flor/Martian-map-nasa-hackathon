from fastapi import APIRouter, HTTPException, Query

from core.config import get_settings
from geospatial.raster import RasterInspectionError, inspect_raster
from models.mission import MissionInfo, PlanRequest, PlanResponse, RasterInfo
from services.planner import DEM_NAME, RoutePlanner

router = APIRouter(prefix="/mission", tags=["mission"])
planner = RoutePlanner()


@router.get("", response_model=MissionInfo)
def mission_info() -> MissionInfo:
    return MissionInfo(
        name="Martian Map",
        description="Mars exploration viewer and terrain-aware route-planning prototype.",
        route_profiles=["direct", "low_slope", "conservative"],
        planning_status="ready"
        if (get_settings().data_dir / DEM_NAME).is_file()
        else "not_implemented",
    )


@router.get("/raster", response_model=RasterInfo)
def raster_info(
    path: str = Query(..., description="Raster path relative to the data directory"),
) -> RasterInfo:
    data_root = get_settings().data_dir.resolve()
    requested = (data_root / path).resolve()

    if not requested.is_relative_to(data_root):
        raise HTTPException(
            status_code=400,
            detail="Raster path must stay inside the data directory.",
        )
    if not requested.is_file():
        raise HTTPException(status_code=404, detail="Raster file not found.")

    try:
        result = inspect_raster(requested)
    except RasterInspectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return RasterInfo(**result)


@router.post("/plan", response_model=PlanResponse)
def plan_route(payload: PlanRequest) -> PlanResponse:
    try:
        return planner.plan(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
