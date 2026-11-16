from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import CRS

from geospatial.raster import RasterDataError, read_dem
from tests.helpers import write_raster


def test_dem_applies_scale_and_offset(
    tmp_path: Path,
    mars_crs: CRS,
    mars_transform,
) -> None:
    values = np.full(
        (9, 9),
        100.0,
        dtype=np.float32,
    )

    path = write_raster(
        tmp_path / "scaled_dem.tif",
        values,
        mars_crs,
        mars_transform,
        unit="m",
    )

    with rasterio.open(path, "r+") as dataset:
        dataset.scales = (2.0,)
        dataset.offsets = (10.0,)

    dem = read_dem(path)

    # Physical elevation = raw value * scale + offset.
    assert dem.values[4, 4] == pytest.approx(210.0)


def test_dem_without_vertical_unit_is_rejected(
    tmp_path: Path,
    mars_crs: CRS,
    mars_transform,
) -> None:
    values = np.full(
        (9, 9),
        100.0,
        dtype=np.float32,
    )

    path = write_raster(
        tmp_path / "unknown_unit_dem.tif",
        values,
        mars_crs,
        mars_transform,
        unit=None,
    )

    with pytest.raises(RasterDataError, match="vertical unit"):
        read_dem(path)


def test_earth_projected_crs_is_rejected(
    tmp_path: Path,
    mars_transform,
) -> None:
    values = np.full(
        (9, 9),
        100.0,
        dtype=np.float32,
    )

    earth_crs = CRS.from_epsg(3857)

    path = write_raster(
        tmp_path / "earth_dem.tif",
        values,
        earth_crs,
        mars_transform,
        unit="m",
    )

    with pytest.raises(RasterDataError):
        read_dem(path)
