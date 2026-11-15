from dataclasses import dataclass
from math import isfinite

SLOPE_REFERENCE_DEG = 15.0


@dataclass(frozen=True, slots=True)
class CostWeights:
    slope: float
    hazard: float
    uncertainty: float
    elevation_change: float

    def __post_init__(self) -> None:
        values = (
            self.slope,
            self.hazard,
            self.uncertainty,
            self.elevation_change,
        )

        if any(not isfinite(value) or value < 0.0 for value in values):
            raise ValueError("Cost weights must be finite and non-negative.")


PROFILE_WEIGHTS: dict[str, CostWeights] = {
    "direct": CostWeights(
        slope=0.0,
        hazard=0.0,
        uncertainty=0.0,
        elevation_change=0.0,
    ),
    "low_slope": CostWeights(
        slope=10.0,
        hazard=0.0,
        uncertainty=0.0,
        elevation_change=0.0,
    ),
    "conservative": CostWeights(
        slope=10.0,
        hazard=8.0,
        uncertainty=6.0,
        elevation_change=0.10,
    ),
}


def edge_cost(
    distance_m: float,
    slope_start_deg: float,
    slope_end_deg: float,
    hazard_start: float,
    hazard_end: float,
    uncertainty_start: float,
    uncertainty_end: float,
    elevation_start_m: float,
    elevation_end_m: float,
    weights: CostWeights,
) -> float:
    """Calculate the non-negative traversal cost between two cells."""

    inputs = (
        distance_m,
        slope_start_deg,
        slope_end_deg,
        hazard_start,
        hazard_end,
        uncertainty_start,
        uncertainty_end,
        elevation_start_m,
        elevation_end_m,
    )

    if any(not isfinite(value) for value in inputs):
        raise ValueError("Movement cost inputs must be finite.")

    if distance_m <= 0.0:
        raise ValueError("Movement distance must be positive.")

    if not (0.0 <= slope_start_deg <= 90.0):
        raise ValueError("Starting slope must be between 0 and 90 degrees.")

    if not (0.0 <= slope_end_deg <= 90.0):
        raise ValueError("Ending slope must be between 0 and 90 degrees.")

    for value in (
        hazard_start,
        hazard_end,
        uncertainty_start,
        uncertainty_end,
    ):
        if not 0.0 <= value <= 1.0:
            raise ValueError("Hazard and uncertainty values must be in [0, 1].")

    mean_slope = (slope_start_deg + slope_end_deg) / 2.0
    normalized_slope = mean_slope / SLOPE_REFERENCE_DEG

    mean_hazard = (hazard_start + hazard_end) / 2.0
    mean_uncertainty = (uncertainty_start + uncertainty_end) / 2.0

    elevation_change = abs(elevation_end_m - elevation_start_m)

    terrain_factor = (
        1.0
        + weights.slope * normalized_slope**2
        + weights.hazard * mean_hazard
        + weights.uncertainty * mean_uncertainty
    )

    return distance_m * terrain_factor + weights.elevation_change * elevation_change
