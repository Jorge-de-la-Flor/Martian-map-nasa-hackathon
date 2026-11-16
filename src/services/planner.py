from __future__ import annotations

from pathlib import Path

import numpy as np

from geospatial.raster import (
    RasterDataError,
    read_aligned_layer,
    read_dem,
    resolve_data_path,
)
from geospatial.terrain import calculate_slope
from models.mission import (
    ElevationResponse,
    PlanRequest,
    PlanResponse,
    ProfileSample,
    RoutePoint,
)
from services.astar import astar_search
from services.cost import PROFILE_WEIGHTS
from services.metrics import measure_route


class RoutePlanner:
    def __init__(
        self,
        data_dir: Path,
        max_cells: int = 10_000_000,
        max_expansions: int = 2_000_000,
        max_output_points: int = 10_000,
    ) -> None:
        if max_cells < 9:
            raise ValueError("max_cells must be at least 9.")

        if max_expansions < 1:
            raise ValueError("max_expansions must be positive.")

        if max_output_points < 2:
            raise ValueError("max_output_points must be at least 2.")

        self.data_dir = data_dir.expanduser().resolve()
        self.max_cells = max_cells
        self.max_expansions = max_expansions
        self.max_output_points = max_output_points

    def _load_optional_layer(
        self,
        relative_path: str | None,
        dem,
    ) -> tuple[np.ndarray, np.ndarray] | None:
        if relative_path is None:
            return None

        path = resolve_data_path(
            self.data_dir,
            relative_path,
        )

        return read_aligned_layer(
            path=path,
            reference=dem,
            normalized=True,
        )

    def plan(self, request: PlanRequest) -> PlanResponse:
        dem_file = resolve_data_path(
            self.data_dir,
            request.dem_path,
        )

        dem = read_dem(
            dem_file,
            max_cells=self.max_cells,
        )

        slope = calculate_slope(dem)

        traversable = dem.valid_mask & np.isfinite(slope)

        hazard = np.zeros(dem.shape, dtype=np.float64)
        uncertainty = np.ones(dem.shape, dtype=np.float64)
        blocked = np.zeros(dem.shape, dtype=bool)

        hazard_layer = self._load_optional_layer(
            request.hazard_path,
            dem,
        )

        if hazard_layer is not None:
            hazard_values, hazard_valid = hazard_layer

            hazard = np.where(
                hazard_valid,
                hazard_values,
                0.0,
            )

            # A missing hazard observation is unknown, not safe.
            uncertainty[~hazard_valid] = 1.0

        uncertainty_layer = self._load_optional_layer(
            request.uncertainty_path,
            dem,
        )

        if uncertainty_layer is not None:
            uncertainty_values, uncertainty_valid = uncertainty_layer

            uncertainty = np.where(
                uncertainty_valid,
                uncertainty_values,
                1.0,
            )

            if hazard_layer is not None:
                uncertainty[~hazard_valid] = 1.0
            else:
                # Without a hazard layer, hazard-related uncertainty remains unknown.
                uncertainty.fill(1.0)

        blocked_layer = self._load_optional_layer(
            request.blocked_path,
            dem,
        )

        if blocked_layer is not None:
            blocked_values, blocked_valid = blocked_layer

            # NoData in an explicitly supplied obstacle layer is not assumed safe.
            blocked = ~blocked_valid | (blocked_values >= 0.5)

        traversable &= ~blocked

        start = dem.world_to_cell(
            request.start.x_m,
            request.start.y_m,
        )

        destination = dem.world_to_cell(
            request.destination.x_m,
            request.destination.y_m,
        )

        result = astar_search(
            elevation=dem.values,
            slope_deg=slope,
            traversable=traversable,
            hazard=hazard,
            uncertainty=uncertainty,
            transform=dem.transform,
            start=start,
            goal=destination,
            weights=PROFILE_WEIGHTS[request.profile],
            max_expansions=self.max_expansions,
            max_slope_deg=request.max_slope_deg,
        )

        measurements = measure_route(
            path=result.path,
            elevation=dem.values,
            slope_deg=slope,
            hazard=hazard,
            uncertainty=uncertainty,
            transform=dem.transform,
            total_cost=result.total_cost,
            expanded_nodes=result.expanded_nodes,
            walking_speed_m_s=request.walking_speed_m_s,
        )

        selected_indices = np.unique(
            np.linspace(
                0,
                len(result.path) - 1,
                min(
                    len(result.path),
                    self.max_output_points,
                ),
                dtype=int,
            )
        )

        route_points: list[RoutePoint] = []
        elevation_profile: list[ProfileSample] = []

        for index in selected_indices:
            row, column = result.path[int(index)]

            x_m, y_m = dem.cell_center(row, column)

            elevation_m = float(dem.values[row, column])
            slope_value = float(slope[row, column])

            route_points.append(
                RoutePoint(
                    row=row,
                    column=column,
                    x_m=x_m,
                    y_m=y_m,
                    elevation_m=elevation_m,
                    slope_deg=slope_value,
                )
            )

            elevation_profile.append(
                ProfileSample(
                    distance_m=measurements.cumulative_distance_m[int(index)],
                    elevation_m=elevation_m,
                    slope_deg=slope_value,
                )
            )

        limitations = [
            "The route estimates terrain difficulty; it does not certify astronaut safety.",
            "Small rocks, loose sand, local hazards, and recent surface changes may be unresolved.",
            "Raster border cells without a complete Horn neighborhood are not traversable.",
            "Hazard exposure represents only the supplied hazard layer.",
            "Uncertainty and cost weights are model parameters, not validated universal safety limits.",
        ]

        if request.hazard_path is None:
            limitations.append("No hazard layer was supplied. Hazard conditions are unknown.")

        if request.uncertainty_path is None:
            limitations.append("No uncertainty layer was supplied. Uncertainty defaults to 1.0.")

        if request.blocked_path is None:
            limitations.append("No explicit obstacle layer was supplied.")

        if request.max_slope_deg is not None:
            limitations.append(
                "The maximum slope is a user-supplied planning constraint, not a universal safety limit."
            )

        if request.walking_speed_m_s is not None:
            limitations.append(
                "Duration assumes a constant user-supplied speed and is not a validated Marswalk prediction."
            )

        return PlanResponse(
            status="planned",
            message="A terrain-aware route was computed using the selected cost profile.",
            profile=request.profile,
            dem_path=request.dem_path,
            crs=dem.crs.to_string(),
            route=route_points,
            elevation_profile=elevation_profile,
            metrics=measurements.metrics,
            limitations=limitations,
        )

    def query_elevation(
        self,
        dem_path: str,
        x_m: float,
        y_m: float,
    ) -> ElevationResponse:
        path = resolve_data_path(
            self.data_dir,
            dem_path,
        )

        dem = read_dem(
            path,
            max_cells=self.max_cells,
        )

        row, column = dem.world_to_cell(x_m, y_m)

        if not dem.valid_mask[row, column]:
            raise RasterDataError("The selected cell has no valid elevation data.")

        slope = calculate_slope(dem)
        slope_value = float(slope[row, column])

        return ElevationResponse(
            x_m=x_m,
            y_m=y_m,
            row=row,
            column=column,
            elevation_m=float(dem.values[row, column]),
            slope_deg=(slope_value if np.isfinite(slope_value) else None),
            crs=dem.crs.to_string(),
        )
