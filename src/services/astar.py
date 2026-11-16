from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import hypot, isfinite
from typing import Any

import numpy as np

from services.cost import CostWeights, edge_cost


class NoPathError(RuntimeError):
    """Raised when no traversable route connects the requested cells."""


class PlanningLimitError(RuntimeError):
    """Raised when the search reaches its configured expansion limit."""


@dataclass(slots=True)
class AStarResult:
    path: list[tuple[int, int]]
    total_cost: float
    expanded_nodes: int


NEIGHBORS = (
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
)


def _world_point(
    transform: Any,
    row: int,
    column: int,
) -> tuple[float, float]:
    x, y = transform * (column + 0.5, row + 0.5)
    return float(x), float(y)


def _movement_distance(
    transform: Any,
    row_a: int,
    col_a: int,
    row_b: int,
    col_b: int,
) -> float:
    x_a, y_a = _world_point(transform, row_a, col_a)
    x_b, y_b = _world_point(transform, row_b, col_b)

    distance = hypot(x_b - x_a, y_b - y_a)

    if not isfinite(distance) or distance <= 0.0:
        raise ValueError("The raster transform produced an invalid movement distance.")

    return distance


def _heuristic(
    transform: Any,
    row: int,
    column: int,
    goal: tuple[int, int],
) -> float:
    x, y = _world_point(transform, row, column)
    goal_x, goal_y = _world_point(transform, goal[0], goal[1])

    return hypot(goal_x - x, goal_y - y)


def astar_search(
    elevation: np.ndarray,
    slope_deg: np.ndarray,
    traversable: np.ndarray,
    hazard: np.ndarray,
    uncertainty: np.ndarray,
    transform: Any,
    start: tuple[int, int],
    goal: tuple[int, int],
    weights: CostWeights,
    max_expansions: int = 2_000_000,
    max_slope_deg: float | None = None,
) -> AStarResult:
    """Find a minimum-cost route over an eight-connected raster grid."""

    shape = elevation.shape

    arrays = (
        slope_deg,
        traversable,
        hazard,
        uncertainty,
    )

    if any(array.shape != shape for array in arrays):
        raise ValueError("All terrain arrays must have identical dimensions.")

    if elevation.ndim != 2:
        raise ValueError("The elevation grid must be two-dimensional.")

    if max_expansions < 1:
        raise ValueError("max_expansions must be positive.")

    if max_slope_deg is not None:
        if not isfinite(max_slope_deg) or not 0.0 <= max_slope_deg <= 90.0:
            raise ValueError("Maximum slope must be between 0 and 90 degrees.")

    if not isinstance(weights, CostWeights):
        raise TypeError("weights must be a CostWeights instance.")

    height, width = shape

    for point in (start, goal):
        row, column = point

        if not (0 <= row < height and 0 <= column < width):
            raise ValueError("Start or destination lies outside the raster.")

    if start == goal:
        raise ValueError("Start and destination must map to different DEM cells.")

    # Reject invalid normalized layers instead of silently interpreting them.
    finite_hazard = hazard[np.isfinite(hazard)]
    finite_uncertainty = uncertainty[np.isfinite(uncertainty)]

    if np.any((finite_hazard < 0.0) | (finite_hazard > 1.0)):
        raise ValueError("Hazard values must be normalized to [0, 1].")

    if np.any((finite_uncertainty < 0.0) | (finite_uncertainty > 1.0)):
        raise ValueError("Uncertainty values must be normalized to [0, 1].")

    valid = (
        traversable.astype(bool)
        & np.isfinite(elevation)
        & np.isfinite(slope_deg)
        & np.isfinite(hazard)
        & np.isfinite(uncertainty)
        & (slope_deg >= 0.0)
        & (slope_deg <= 90.0)
    )

    if max_slope_deg is not None:
        valid &= slope_deg <= max_slope_deg

    if not valid[start]:
        raise ValueError("The starting cell is not traversable.")

    if not valid[goal]:
        raise ValueError("The destination cell is not traversable.")

    start_row, start_col = start
    goal_row, goal_col = goal

    g_score = np.full(shape, np.inf, dtype=np.float64)
    parent_row = np.full(shape, -1, dtype=np.int32)
    parent_col = np.full(shape, -1, dtype=np.int32)
    closed = np.zeros(shape, dtype=bool)

    g_score[start] = 0.0

    open_heap: list[tuple[float, float, int, int]] = [
        (
            _heuristic(transform, start_row, start_col, goal),
            0.0,
            start_row,
            start_col,
        )
    ]

    expanded_nodes = 0

    while open_heap:
        _, current_cost, row, column = heapq.heappop(open_heap)

        if closed[row, column]:
            continue

        if current_cost > g_score[row, column] + 1e-10:
            continue

        if (row, column) == goal:
            path = [(goal_row, goal_col)]

            while path[-1] != start:
                current_row, current_col = path[-1]

                previous_row = int(parent_row[current_row, current_col])
                previous_col = int(parent_col[current_row, current_col])

                if previous_row < 0 or previous_col < 0:
                    raise NoPathError("Could not reconstruct the computed route.")

                path.append((previous_row, previous_col))

            path.reverse()

            return AStarResult(
                path=path,
                total_cost=float(g_score[goal]),
                expanded_nodes=expanded_nodes,
            )

        if expanded_nodes >= max_expansions:
            raise PlanningLimitError(f"A* reached the expansion limit ({max_expansions:,}).")

        closed[row, column] = True
        expanded_nodes += 1

        for delta_row, delta_col in NEIGHBORS:
            next_row = row + delta_row
            next_col = column + delta_col

            if not (0 <= next_row < height and 0 <= next_col < width):
                continue

            if not valid[next_row, next_col] or closed[next_row, next_col]:
                continue

            is_diagonal = delta_row != 0 and delta_col != 0

            if is_diagonal:
                orthogonal_a = (row + delta_row, column)
                orthogonal_b = (row, column + delta_col)

                if not (valid[orthogonal_a] and valid[orthogonal_b]):
                    continue

            distance_m = _movement_distance(
                transform,
                row,
                column,
                next_row,
                next_col,
            )

            movement_cost = edge_cost(
                distance_m=distance_m,
                slope_start_deg=float(slope_deg[row, column]),
                slope_end_deg=float(slope_deg[next_row, next_col]),
                hazard_start=float(hazard[row, column]),
                hazard_end=float(hazard[next_row, next_col]),
                uncertainty_start=float(uncertainty[row, column]),
                uncertainty_end=float(uncertainty[next_row, next_col]),
                elevation_start_m=float(elevation[row, column]),
                elevation_end_m=float(elevation[next_row, next_col]),
                weights=weights,
            )

            tentative_cost = current_cost + movement_cost

            if tentative_cost + 1e-10 >= g_score[next_row, next_col]:
                continue

            g_score[next_row, next_col] = tentative_cost
            parent_row[next_row, next_col] = row
            parent_col[next_row, next_col] = column

            estimated_total = tentative_cost + _heuristic(
                transform,
                next_row,
                next_col,
                goal,
            )

            heapq.heappush(
                open_heap,
                (
                    estimated_total,
                    tentative_cost,
                    next_row,
                    next_col,
                ),
            )

    raise NoPathError("No traversable route connects the selected points.")
