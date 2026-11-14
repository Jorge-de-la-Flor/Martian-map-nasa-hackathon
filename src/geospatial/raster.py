from pathlib import Path
from typing import Any

import rasterio


class RasterInspectionError(Exception):
    pass


def inspect_raster(path: Path) -> dict[str, Any]:
    try:
        with rasterio.open(path) as dataset:
            bounds = dataset.bounds
            return {
                "file_name": path.name,
                "driver": dataset.driver,
                "width": dataset.width,
                "height": dataset.height,
                "band_count": dataset.count,
                "dtype": dataset.dtypes[0] if dataset.count else None,
                "crs": dataset.crs.to_string() if dataset.crs else None,
                "bounds": {
                    "left": bounds.left,
                    "bottom": bounds.bottom,
                    "right": bounds.right,
                    "top": bounds.top,
                },
                "nodata": dataset.nodata,
                "resolution": list(dataset.res),
            }
    except rasterio.errors.RasterioError as exc:
        raise RasterInspectionError(f"Could not read raster: {exc}") from exc
