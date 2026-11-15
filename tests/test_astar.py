import numpy as np
import pytest
from rasterio.transform import from_origin

from services.astar import NoPathError, astar_search
from services.cost import PROFILE_WEIGHTS


def test_astar_finds_direct_path() -> None:
    elevation = np.zeros((5, 5), dtype=np.float64)
    slope = np.zeros((5, 5), dtype=np.float64)
    traversable = np.ones((5, 5), dtype=bool)
    hazard = np.zeros((5, 5), dtype=np.float64)
    uncertainty = np.zeros((5, 5), dtype=np.float64)

    result = astar_search(
        elevation=elevation,
        slope_deg=slope,
        traversable=traversable,
        hazard=hazard,
        uncertainty=uncertainty,
        transform=from_origin(0, 50, 10, 10),
        start=(2, 0),
        goal=(2, 4),
        weights=PROFILE_WEIGHTS["direct"],
    )

    assert result.path[0] == (2, 0)
    assert result.path[-1] == (2, 4)
    assert result.total_cost == pytest.approx(40.0)
    assert result.expanded_nodes > 0


def test_astar_rejects_identical_cells() -> None:
    elevation = np.zeros((3, 3), dtype=np.float64)
    slope = np.zeros((3, 3), dtype=np.float64)
    traversable = np.ones((3, 3), dtype=bool)
    hazard = np.zeros((3, 3), dtype=np.float64)
    uncertainty = np.zeros((3, 3), dtype=np.float64)

    with pytest.raises(ValueError, match="different DEM cells"):
        astar_search(
            elevation=elevation,
            slope_deg=slope,
            traversable=traversable,
            hazard=hazard,
            uncertainty=uncertainty,
            transform=from_origin(0, 30, 10, 10),
            start=(1, 1),
            goal=(1, 1),
            weights=PROFILE_WEIGHTS["direct"],
        )


def test_astar_does_not_cut_blocked_corners() -> None:
    elevation = np.zeros((2, 2), dtype=np.float64)
    slope = np.zeros((2, 2), dtype=np.float64)

    traversable = np.array(
        [
            [True, False],
            [False, True],
        ]
    )

    hazard = np.zeros((2, 2), dtype=np.float64)
    uncertainty = np.zeros((2, 2), dtype=np.float64)

    with pytest.raises(NoPathError):
        astar_search(
            elevation=elevation,
            slope_deg=slope,
            traversable=traversable,
            hazard=hazard,
            uncertainty=uncertainty,
            transform=from_origin(0, 20, 10, 10),
            start=(0, 0),
            goal=(1, 1),
            weights=PROFILE_WEIGHTS["direct"],
        )


def test_astar_rejects_wrong_array_shape() -> None:
    elevation = np.zeros((5, 5))
    slope = np.zeros((4, 5))
    traversable = np.ones((5, 5), dtype=bool)
    hazard = np.zeros((5, 5))
    uncertainty = np.zeros((5, 5))

    with pytest.raises(ValueError, match="identical dimensions"):
        astar_search(
            elevation=elevation,
            slope_deg=slope,
            traversable=traversable,
            hazard=hazard,
            uncertainty=uncertainty,
            transform=from_origin(0, 50, 10, 10),
            start=(1, 1),
            goal=(3, 3),
            weights=PROFILE_WEIGHTS["direct"],
        )
