from typing import Literal

from pydantic import BaseModel, Field

RouteProfile = Literal["direct", "low_slope", "conservative"]


class MissionInfo(BaseModel):
    name: str
    description: str
    route_profiles: list[RouteProfile]
    planning_status: Literal["not_implemented", "ready"]


class Coordinate(BaseModel):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class PlanRequest(BaseModel):
    start: Coordinate
    destination: Coordinate
    profile: RouteProfile = "low_slope"


class PlanResponse(BaseModel):
    status: Literal["not_implemented", "outside_coverage", "no_path", "planned"]
    profile: RouteProfile
    message: str
    route: list[Coordinate] = Field(default_factory=list)
    distance_m: float | None = None


class RasterInfo(BaseModel):
    file_name: str
    driver: str
    width: int
    height: int
    band_count: int
    dtype: str | None
    crs: str | None
    bounds: dict[str, float]
    nodata: float | None
    resolution: list[float]
