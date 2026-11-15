from heapq import heappop, heappush
from math import cos, hypot, radians

import numpy as np
import rasterio
from pyproj import CRS, Transformer

from core.config import get_settings
from models.mission import Coordinate, PlanRequest, PlanResponse

Cell = tuple[int, int]
DEM_NAME = "mount-sharp-boxwork-dem.tif"
SLOPE_WEIGHT = {"direct": 0, "low_slope": 6, "conservative": 20}
NEIGHBORS = tuple(
    (row, column) for row in (-1, 0, 1) for column in (-1, 0, 1) if row or column
)


def shortest_path(
    heights: np.ndarray,
    start: Cell,
    end: Cell,
    east_step: float,
    north_step: float,
    slope_weight: int,
) -> list[Cell]:
    height, width = heights.shape
    valid = np.isfinite(heights)
    moves = [(dr, dc, hypot(dr * north_step, dc * east_step)) for dr, dc in NEIGHBORS]
    costs = {start: 0.0}
    parent: dict[Cell, Cell] = {}
    queue = [(0.0, 0.0, start)]
    while queue:
        _, cost, cell = heappop(queue)
        if cost > costs[cell]:
            continue
        if cell == end:
            path = [cell]
            while cell in parent:
                cell = parent[cell]
                path.append(cell)
            return path[::-1]
        row, col = cell
        for dr, dc, length in moves:
            other = (row + dr, col + dc)
            rr, cc = other
            if not (0 <= rr < height and 0 <= cc < width and valid[other]):
                continue
            if dr and dc and not (valid[row, cc] and valid[rr, col]):
                continue
            grade = (heights[other] - heights[cell]) / length
            candidate = cost + length * (1.0 + slope_weight * grade * grade)
            if candidate >= costs.get(other, float("inf")):
                continue
            costs[other] = candidate
            parent[other] = cell
            remaining = hypot((end[0] - rr) * north_step, (end[1] - cc) * east_step)
            heappush(queue, (candidate + remaining, candidate, other))
    return []


class RoutePlanner:
    def plan(self, request: PlanRequest) -> PlanResponse:
        if request.start == request.destination:
            raise ValueError("Start and destination must be different.")

        dem = get_settings().data_dir / DEM_NAME
        if not dem.is_file():
            return PlanResponse(
                status="not_implemented",
                profile=request.profile,
                message="The local Mount Sharp elevation model is unavailable.",
            )

        with rasterio.open(dem) as raster:
            crs = CRS.from_user_input("ESRI:103885")
            if raster.crs != crs or not raster.transform.is_rectilinear:
                raise ValueError("The local Gale DEM has an unexpected projection.")
            to_grid = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
            to_mars = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
            start, end = [
                raster.index(*to_grid.transform(point.longitude, point.latitude))
                for point in (request.start, request.destination)
            ]
            if any(
                not (0 <= row < raster.height and 0 <= col < raster.width)
                for row, col in (start, end)
            ):
                return PlanResponse(
                    status="outside_coverage",
                    profile=request.profile,
                    message="Both points must be inside the Mount Sharp DEM. Choose points in the Boxwork study area.",
                )
            if start == end:
                raise ValueError(
                    "Start and destination are in the same elevation cell."
                )

            heights = raster.read(1, masked=True).astype("float64").filled(np.nan)
            if not np.isfinite([heights[start], heights[end]]).all():
                return PlanResponse(
                    status="no_path",
                    profile=request.profile,
                    message="An endpoint is in a cell without valid elevation. Choose a nearby point.",
                )
            latitude = (request.start.latitude + request.destination.latitude) / 2
            cells = shortest_path(
                heights,
                start,
                end,
                raster.res[0] * cos(radians(latitude)),
                raster.res[1],
                SLOPE_WEIGHT[request.profile],
            )
            if not cells:
                return PlanResponse(
                    status="no_path",
                    profile=request.profile,
                    message="No continuous path through valid elevation cells links these points.",
                )
            x, y = raster.xy(*zip(*cells))
        lon, lat = to_mars.transform(x, y)
        route = [Coordinate(longitude=a, latitude=b) for a, b in zip(lon, lat)]
        route[0], route[-1] = request.start, request.destination
        return PlanResponse(
            status="planned",
            profile=request.profile,
            message="Mount Sharp route estimated from the USGS elevation model.",
            route=route,
            distance_m=crs.get_geod().line_length(
                [point.longitude for point in route],
                [point.latitude for point in route],
            ),
        )
