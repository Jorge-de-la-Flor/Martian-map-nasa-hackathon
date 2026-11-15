from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RouteProfile = Literal[
    "direct",
    "low_slope",
    "conservative",
]

LayerCategory = Literal[
    "topographic",
    "optical",
    "thermal",
    "spectral",
    "radiation",
    "atmospheric",
    "chemical",
    "geophysical",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
    )


class MissionInfo(StrictModel):
    name: str
    description: str
    route_profiles: list[RouteProfile]
    planning_status: Literal["awaiting_data", "ready"]
    region_name: str | None = None


class ProjectedCoordinate(StrictModel):
    x_m: float
    y_m: float


class PlanRequest(StrictModel):
    dem_path: str = Field(
        min_length=1,
        max_length=255,
    )

    start: ProjectedCoordinate
    destination: ProjectedCoordinate

    profile: RouteProfile = "low_slope"

    hazard_path: str | None = Field(
        default=None,
        max_length=255,
    )

    uncertainty_path: str | None = Field(
        default=None,
        max_length=255,
    )

    blocked_path: str | None = Field(
        default=None,
        max_length=255,
    )

    max_slope_deg: float | None = Field(
        default=None,
        gt=0,
        le=90,
    )

    walking_speed_m_s: float | None = Field(
        default=None,
        gt=0,
    )


class RoutePoint(StrictModel):
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    x_m: float
    y_m: float
    elevation_m: float
    slope_deg: float = Field(ge=0, le=90)


class ProfileSample(StrictModel):
    distance_m: float = Field(ge=0)
    elevation_m: float
    slope_deg: float = Field(ge=0, le=90)


class RouteMetrics(StrictModel):
    distance_m: float = Field(ge=0)
    ascent_m: float = Field(ge=0)
    descent_m: float = Field(ge=0)
    max_slope_deg: float = Field(ge=0, le=90)
    mean_slope_deg: float = Field(ge=0, le=90)
    total_cost: float = Field(ge=0)
    uncertain_distance_m: float = Field(ge=0)
    hazard_exposure_distance_m: float = Field(ge=0)
    duration_s: float | None = Field(
        default=None,
        ge=0,
    )
    expanded_nodes: int = Field(ge=0)


class PlanResponse(StrictModel):
    status: Literal["planned"]
    message: str
    profile: RouteProfile
    dem_path: str
    crs: str
    route: list[RoutePoint]
    elevation_profile: list[ProfileSample]
    metrics: RouteMetrics
    limitations: list[str] = Field(default_factory=list)


class ElevationResponse(StrictModel):
    x_m: float
    y_m: float
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    elevation_m: float
    slope_deg: float | None = Field(
        default=None,
        ge=0,
        le=90,
    )
    crs: str


class RasterInfo(StrictModel):
    file_name: str
    driver: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    band_count: int = Field(ge=0)
    dtype: str | None
    crs: str | None
    ellipsoid_semi_major_m: float | None
    bounds: dict[str, float]
    nodata: float | None
    resolution: list[float]
    transform: list[float]
    band_unit: str | None
    scale: float
    offset: float


class LayerInfo(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    name: str
    category: LayerCategory
    mission: str
    instrument: str
    source_url: str
    role: str
    resolution_m: float | None = Field(
        default=None,
        gt=0,
    )
    local_path: str | None = None
    available: bool
    asset_url: str | None = None
    notes: str


class DataCatalogResponse(StrictModel):
    region_name: str | None = None
    region_status: Literal["not_selected", "selected"]
    layers: list[LayerInfo]
    available_categories: list[str]
