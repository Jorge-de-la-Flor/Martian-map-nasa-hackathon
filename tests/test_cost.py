import pytest

from services.cost import CostWeights, edge_cost


def test_flat_unpenalized_cost_equals_distance() -> None:
    weights = CostWeights(
        slope=0.0,
        hazard=0.0,
        uncertainty=0.0,
        elevation_change=0.0,
    )

    cost = edge_cost(
        distance_m=100.0,
        slope_start_deg=0.0,
        slope_end_deg=0.0,
        hazard_start=0.0,
        hazard_end=0.0,
        uncertainty_start=0.0,
        uncertainty_end=0.0,
        elevation_start_m=100.0,
        elevation_end_m=100.0,
        weights=weights,
    )

    assert cost == pytest.approx(100.0)


def test_steeper_terrain_has_higher_cost() -> None:
    weights = CostWeights(
        slope=10.0,
        hazard=0.0,
        uncertainty=0.0,
        elevation_change=0.0,
    )

    flat_cost = edge_cost(
        distance_m=100.0,
        slope_start_deg=0.0,
        slope_end_deg=0.0,
        hazard_start=0.0,
        hazard_end=0.0,
        uncertainty_start=0.0,
        uncertainty_end=0.0,
        elevation_start_m=100.0,
        elevation_end_m=100.0,
        weights=weights,
    )

    steep_cost = edge_cost(
        distance_m=100.0,
        slope_start_deg=15.0,
        slope_end_deg=15.0,
        hazard_start=0.0,
        hazard_end=0.0,
        uncertainty_start=0.0,
        uncertainty_end=0.0,
        elevation_start_m=100.0,
        elevation_end_m=100.0,
        weights=weights,
    )

    assert steep_cost > flat_cost


def test_hazard_increases_cost() -> None:
    weights = CostWeights(
        slope=0.0,
        hazard=8.0,
        uncertainty=0.0,
        elevation_change=0.0,
    )

    cost = edge_cost(
        distance_m=100.0,
        slope_start_deg=0.0,
        slope_end_deg=0.0,
        hazard_start=1.0,
        hazard_end=1.0,
        uncertainty_start=0.0,
        uncertainty_end=0.0,
        elevation_start_m=100.0,
        elevation_end_m=100.0,
        weights=weights,
    )

    assert cost == pytest.approx(900.0)


@pytest.mark.parametrize(
    "weights",
    [
        (-1.0, 0.0, 0.0, 0.0),
        (0.0, -1.0, 0.0, 0.0),
        (0.0, 0.0, -1.0, 0.0),
        (0.0, 0.0, 0.0, -1.0),
    ],
)
def test_negative_weights_are_rejected(weights) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        CostWeights(*weights)


def test_non_finite_weights_are_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        CostWeights(
            slope=float("nan"),
            hazard=0.0,
            uncertainty=0.0,
            elevation_change=0.0,
        )


def test_cost_is_never_less_than_horizontal_distance() -> None:
    weights = CostWeights(
        slope=10.0,
        hazard=8.0,
        uncertainty=6.0,
        elevation_change=0.1,
    )

    cost = edge_cost(
        distance_m=100.0,
        slope_start_deg=12.0,
        slope_end_deg=15.0,
        hazard_start=0.4,
        hazard_end=0.6,
        uncertainty_start=0.3,
        uncertainty_end=0.8,
        elevation_start_m=100.0,
        elevation_end_m=125.0,
        weights=weights,
    )

    assert cost >= 100.0
