from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS


def write_raster(
    path: Path,
    values: np.ndarray,
    crs: CRS,
    transform,
    nodata: float = -9999.0,
    unit: str | None = "m",
) -> Path:
    """Create a single-band synthetic GeoTIFF for automated tests."""

    data = np.asarray(
        values,
        dtype=np.float32,
    )

    if data.ndim != 2 or data.size == 0:
        raise ValueError("Test raster must be a non-empty 2D array.")

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored = np.where(
        np.isfinite(data),
        data,
        nodata,
    ).astype(np.float32)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs=crs.to_wkt(),
        transform=transform,
        nodata=nodata,
        compress="deflate",
    ) as dataset:
        dataset.write(stored, 1)

        if unit is not None:
            dataset.set_band_unit(1, unit)

    return path
