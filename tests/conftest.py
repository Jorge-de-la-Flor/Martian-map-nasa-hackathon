from pathlib import Path

import numpy as np
import pytest
from pyproj import CRS
from rasterio.transform import from_origin

from tests.helpers import write_raster

MARS_PROJ4 = (
    "+proj=eqc "
    "+lat_ts=-4.6 "
    "+lat_0=-4.6 "
    "+lon_0=137.4 "
    "+a=3396190 "
    "+b=3376200 "
    "+units=m "
    "+no_defs "
    "+type=crs"
)


@pytest.fixture
def mars_crs() -> CRS:
    return CRS.from_proj4(MARS_PROJ4)


@pytest.fixture
def mars_transform():
    return from_origin(
        -205.0,
        205.0,
        10.0,
        10.0,
    )


@pytest.fixture
def flat_dem_file(
    tmp_path: Path,
    mars_crs: CRS,
    mars_transform,
) -> Path:
    values = np.full(
        (41, 41),
        1000.0,
        dtype=np.float32,
    )

    return write_raster(
        tmp_path / "flat_dem.tif",
        values,
        mars_crs,
        mars_transform,
    )
