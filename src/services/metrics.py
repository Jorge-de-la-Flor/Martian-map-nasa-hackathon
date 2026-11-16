from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite
from typing import Any

import numpy as np

from models.mission import RouteMetrics

EXPOSURE_THRESHOLD = 0.5


@dataclass(slots=True)
class RouteMeasurements:
    metrics: RouteMetrics
    cumulative_distance_m: list[float]


def _point(
    transform: Any,
    row: int,
    column: int,
) -> tuple[float, float]:
    x, y = transform * (
        column + 0.5,
        row + 0.5,
    )

    return float(x), float(y)


def measure_route(
    path: list[tuple[int, int]],
    elevation: np.ndarray,
    slope_deg: np.ndarray,
    hazard: np.ndarray,
    uncertainty: np.ndarray,
    transform: Any,
    total_cost: float,
    expanded_nodes: int,
    walking_speed_m_s: float | None = None,
) -> RouteMeasurements:
    if len(path) < 2:
        raise ValueError("A route must contain at least two cells.")

    shape = elevation.shape

    if any(
        array.shape != shape
        for array in (
            slope_deg,
            hazard,
            uncertainty,
        )
    ):
        raise ValueError("All metric arrays must have identical dimensions.")

    if not isfinite(total_cost) or total_cost < 0.0:
        raise ValueError("Total route cost must be finite and non-negative.")

    if expanded_nodes < 0:
        raise ValueError("Expanded node count cannot be negative.")

    if walking_speed_m_s is not None:
        if not isfinite(walking_speed_m_s) or walking_speed_m_s <= 0.0:
            raise ValueError("Walking speed must be finite and positive.")

    elevations: list[float] = []
    slopes: list[float] = []

    for row, column in path:
        if not (0 <= row < shape[0] and 0 <= column < shape[1]):
            raise ValueError("Route contains a cell outside the raster.")

        z = float(elevation[row, column])
        slope = float(slope_deg[row, column])
        hazard_value = float(hazard[row, column])
        uncertainty_value = float(uncertainty[row, column])

        if not all(
            isfinite(value)
            for value in (
                z,
                slope,
                hazard_value,
                uncertainty_value,
            )
        ):
            raise ValueError("Route contains invalid terrain values.")

        if not 0.0 <= slope <= 90.0:
            raise ValueError("Route contains an invalid slope value.")

        if not 0.0 <= hazard_value <= 1.0:
            raise ValueError("Hazard values must be in [0, 1].")

        if not 0.0 <= uncertainty_value <= 1.0:
            raise ValueError("Uncertainty values must be in [0, 1].")

        elevations.append(z)
        slopes.append(slope)

    distance_m = 0.0
    ascent_m = 0.0
    descent_m = 0.0
    weighted_slope_sum = 0.0
    uncertain_distance_m = 0.0
    hazard_exposure_distance_m = 0.0

    cumulative_distance_m = [0.0]

    for index, (current, following) in enumerate(zip(path, path[1:])):
        row_a, col_a = current
        row_b, col_b = following

        x_a, y_a = _point(
            transform,
            row_a,
            col_a,
        )

        x_b, y_b = _point(
            transform,
            row_b,
            col_b,
        )

        segment_distance = hypot(
            x_b - x_a,
            y_b - y_a,
        )

        if not isfinite(segment_distance) or segment_distance <= 0.0:
            raise ValueError("Route contains a zero-length or invalid segment.")

        elevation_change = elevations[index + 1] - elevations[index]

        ascent_m += max(elevation_change, 0.0)
        descent_m += max(-elevation_change, 0.0)

        mean_segment_slope = (slopes[index] + slopes[index + 1]) / 2.0

        mean_segment_hazard = (float(hazard[row_a, col_a]) + float(hazard[row_b, col_b])) / 2.0

        mean_segment_uncertainty = (
            float(uncertainty[row_a, col_a]) + float(uncertainty[row_b, col_b])
        ) / 2.0

        weighted_slope_sum += segment_distance * mean_segment_slope

        if mean_segment_uncertainty >= EXPOSURE_THRESHOLD:
            uncertain_distance_m += segment_distance

        if mean_segment_hazard >= EXPOSURE_THRESHOLD:
            hazard_exposure_distance_m += segment_distance

        distance_m += segment_distance

        cumulative_distance_m.append(distance_m)

    if distance_m <= 0.0:
        raise ValueError("Route distance must be positive.")

    mean_slope = weighted_slope_sum / distance_m

    duration_s = distance_m / walking_speed_m_s if walking_speed_m_s is not None else None

    return RouteMeasurements(
        metrics=RouteMetrics(
            distance_m=distance_m,
            ascent_m=ascent_m,
            descent_m=descent_m,
            max_slope_deg=max(slopes),
            mean_slope_deg=mean_slope,
            total_cost=total_cost,
            uncertain_distance_m=uncertain_distance_m,
            hazard_exposure_distance_m=hazard_exposure_distance_m,
            duration_s=duration_s,
            expanded_nodes=expanded_nodes,
        ),
        cumulative_distance_m=cumulative_distance_m,
    )
