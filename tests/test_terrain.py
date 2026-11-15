from pathlib import Path

import numpy as np
import pytest

from geospatial.raster import RasterGrid
from geospatial.terrain import calculate_slope


def make_grid(
    values: np.ndarray,
    mars_crs,
    mars_transform,
) -> RasterGrid:
    return RasterGrid(
        path=Path("synthetic.tif"),
        values=values.copy(),
        valid_mask=np.isfinite(values),
        transform=mars_transform,
        crs=mars_crs,
        nodata=None,
        width=values.shape[1],
        height=values.shape[0],
    )


def test_flat_terrain_has_zero_slope(
    mars_crs,
    mars_transform,
) -> None:
    values = np.full((9, 9), 1500.0)

    slope = calculate_slope(make_grid(values, mars_crs, mars_transform))

    assert np.allclose(slope[1:-1, 1:-1], 0.0)
    assert np.isnan(slope[0, 0])


def test_synthetic_ramp_matches_expected_slope(
    mars_crs,
    mars_transform,
) -> None:
    columns = np.arange(9, dtype=np.float64)
    values = np.tile(columns, (9, 1))

    slope = calculate_slope(make_grid(values, mars_crs, mars_transform))

    expected = np.degrees(np.arctan(1.0 / 10.0))

    assert slope[4, 4] == pytest.approx(expected, abs=1e-6)


def test_nodata_neighborhood_is_not_interpolated(
    mars_crs,
    mars_transform,
) -> None:
    values = np.full((9, 9), 100.0)
    values[4, 4] = np.nan

    slope = calculate_slope(make_grid(values, mars_crs, mars_transform))

    assert np.isnan(slope[4, 4])
    assert np.isnan(slope[3, 3])
