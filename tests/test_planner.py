from pathlib import Path

import numpy as np
import pytest

from models.mission import (
    PlanRequest,
    ProjectedCoordinate,
    RouteProfile,
)
from services.astar import NoPathError
from services.planner import RoutePlanner
from tests.helpers import write_raster


def cell_center(transform, row: int, column: int):
    return transform * (
        column + 0.5,
        row + 0.5,
    )


def make_request(
    transform,
    dem_path: str,
    profile: RouteProfile = "direct",
    hazard_path: str | None = None,
    uncertainty_path: str | None = None,
) -> PlanRequest:
    start_x, start_y = cell_center(
        transform,
        20,
        5,
    )

    destination_x, destination_y = cell_center(
        transform,
        20,
        35,
    )

    return PlanRequest(
        dem_path=dem_path,
        start=ProjectedCoordinate(
            x_m=start_x,
            y_m=start_y,
        ),
        destination=ProjectedCoordinate(
            x_m=destination_x,
            y_m=destination_y,
        ),
        profile=profile,
        hazard_path=hazard_path,
        uncertainty_path=uncertainty_path,
    )


def test_planner_computes_route_and_metrics(
    tmp_path: Path,
    mars_transform,
    flat_dem_file: Path,
) -> None:
    planner = RoutePlanner(tmp_path)

    request = make_request(
        mars_transform,
        dem_path="flat_dem.tif",
    )

    result = planner.plan(request)

    assert result.status == "planned"
    assert result.profile == "direct"

    assert result.metrics.distance_m == pytest.approx(300.0)
    assert result.metrics.ascent_m == pytest.approx(0.0)
    assert result.metrics.descent_m == pytest.approx(0.0)

    assert result.metrics.max_slope_deg == pytest.approx(0.0)
    assert result.metrics.mean_slope_deg == pytest.approx(0.0)

    assert len(result.route) >= 2
    assert result.route[0].row == 20
    assert result.route[-1].row == 20


def test_planner_returns_elevation_and_slope(
    tmp_path: Path,
    mars_transform,
    flat_dem_file: Path,
) -> None:
    planner = RoutePlanner(tmp_path)

    x_m, y_m = cell_center(
        mars_transform,
        20,
        20,
    )

    result = planner.query_elevation(
        dem_path="flat_dem.tif",
        x_m=x_m,
        y_m=y_m,
    )

    assert result.elevation_m == pytest.approx(1000.0)
    assert result.slope_deg == pytest.approx(0.0)


def test_planner_rejects_identical_start_and_destination_cells(
    tmp_path: Path,
    mars_transform,
    flat_dem_file: Path,
) -> None:
    planner = RoutePlanner(tmp_path)

    x_m, y_m = cell_center(
        mars_transform,
        20,
        20,
    )

    request = PlanRequest(
        dem_path="flat_dem.tif",
        start=ProjectedCoordinate(
            x_m=x_m,
            y_m=y_m,
        ),
        destination=ProjectedCoordinate(
            x_m=x_m,
            y_m=y_m,
        ),
        profile="direct",
    )

    with pytest.raises(ValueError, match="different DEM cells"):
        planner.plan(request)


def test_planner_does_not_cross_nodata(
    tmp_path: Path,
    mars_crs,
    mars_transform,
) -> None:
    values = np.full(
        (41, 41),
        1000.0,
        dtype=np.float32,
    )

    values[:, 20] = np.nan

    write_raster(
        tmp_path / "barrier_dem.tif",
        values,
        mars_crs,
        mars_transform,
    )

    planner = RoutePlanner(tmp_path)

    request = make_request(
        mars_transform,
        dem_path="barrier_dem.tif",
    )

    with pytest.raises(NoPathError):
        planner.plan(request)


def test_conservative_profile_avoids_high_hazard_corridor(
    tmp_path: Path,
    mars_crs,
    mars_transform,
    flat_dem_file: Path,
) -> None:
    hazard = np.zeros(
        (41, 41),
        dtype=np.float32,
    )

    hazard[15:26, 19:22] = 1.0

    uncertainty = np.zeros(
        (41, 41),
        dtype=np.float32,
    )

    write_raster(
        tmp_path / "hazard.tif",
        hazard,
        mars_crs,
        mars_transform,
        unit="1",
    )

    write_raster(
        tmp_path / "uncertainty.tif",
        uncertainty,
        mars_crs,
        mars_transform,
        unit="1",
    )

    planner = RoutePlanner(tmp_path)

    common = {
        "dem_path": "flat_dem.tif",
        "hazard_path": "hazard.tif",
        "uncertainty_path": "uncertainty.tif",
    }

    direct = planner.plan(
        make_request(
            mars_transform,
            profile="direct",
            **common,
        )
    )

    conservative = planner.plan(
        make_request(
            mars_transform,
            profile="conservative",
            **common,
        )
    )

    assert direct.metrics.hazard_exposure_distance_m > 0.0

    assert conservative.metrics.hazard_exposure_distance_m == pytest.approx(0.0)

    assert conservative.metrics.distance_m > direct.metrics.distance_m


def test_planner_rejects_misaligned_auxiliary_layer(
    tmp_path: Path,
    mars_crs,
    mars_transform,
    flat_dem_file: Path,
) -> None:
    hazard = np.zeros(
        (41, 41),
        dtype=np.float32,
    )

    misaligned_transform = type(mars_transform)(
        mars_transform.a,
        mars_transform.b,
        mars_transform.c + 5.0,
        mars_transform.d,
        mars_transform.e,
        mars_transform.f,
    )

    write_raster(
        tmp_path / "misaligned_hazard.tif",
        hazard,
        mars_crs,
        misaligned_transform,
        unit="1",
    )

    planner = RoutePlanner(tmp_path)

    request = make_request(
        mars_transform,
        dem_path="flat_dem.tif",
        profile="conservative",
        hazard_path="misaligned_hazard.tif",
    )

    with pytest.raises(ValueError, match="pixel-aligned"):
        planner.plan(request)
