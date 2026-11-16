"""Extract a native-resolution window of the Gale DEM around the boxwork sites."""

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEM_URL = (
    "https://asc-pds-services.s3.us-west-2.amazonaws.com/"
    "mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif"
)
MARS_RADIUS_M = 3_396_190
PADDING_CELLS = 150
NODATA = -9999.0


def prepare_dem(source: str, output: Path) -> dict:
    sites = json.loads(
        (DATA_DIR / "mount-sharp-boxwork-sites.json").read_text(encoding="utf-8")
    )["sites"]
    with (
        rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="30"),
        rasterio.open(source) as dem,
    ):
        if dem.crs is None or dem.count != 1 or dem.res != (1.0, 1.0):
            raise ValueError("Expected a single-band 1 m DEM with a CRS.")
        crs = CRS.from_wkt(dem.crs.to_wkt())
        if not (
            crs.is_projected
            and crs.ellipsoid.semi_major_metre == MARS_RADIUS_M
            and crs.ellipsoid.semi_minor_metre == MARS_RADIUS_M
            and all(axis.unit_conversion_factor == 1 for axis in crs.axis_info)
        ):
            raise ValueError("Expected the spherical Gale DEM CRS in metres.")
        transform = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
        cells = {
            site["id"]: dem.index(
                *transform.transform(site["longitude"], site["latitude"], errcheck=True)
            )
            for site in sites
        }
        rows, cols = zip(*cells.values())
        top, left = min(rows) - PADDING_CELLS, min(cols) - PADDING_CELLS
        bottom = max(rows) + PADDING_CELLS + 1
        right = max(cols) + PADDING_CELLS + 1
        if top < 0 or left < 0 or bottom > dem.height or right > dem.width:
            raise ValueError("Requested window extends beyond DEM bounds.")
        window = Window(left, top, right - left, bottom - top)
        elevations = dem.read(1, window=window, masked=True).astype("float32")
        elevations = np.ma.masked_invalid(elevations)
        samples = {
            site_id: elevations[row - top, col - left]
            for site_id, (row, col) in cells.items()
        }
        if any(np.ma.is_masked(elevation) for elevation in samples.values()):
            raise ValueError(
                "A reference waypoint falls on a cell without valid elevation."
            )

        profile = {
            "driver": "GTiff",
            "height": int(window.height),
            "width": int(window.width),
            "count": 1,
            "dtype": "float32",
            "crs": dem.crs,
            "transform": dem.window_transform(window),
            "nodata": NODATA,
            "compress": "deflate",
        }
        with rasterio.open(output, "w", **profile) as dst:
            dst.write(elevations.filled(NODATA), 1)
            dst.units = ("metre",)

    return {
        "raster": str(output),
        "grid_cells": int(elevations.size),
        "valid_cells": int(elevations.count()),
        "dem_elevation_at_rover_waypoints_m": {
            site_id: float(elevation) for site_id, elevation in samples.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", default=DEM_URL, help="Gale DEM URL or local GeoTIFF"
    )
    parser.add_argument(
        "--output", type=Path, default=DATA_DIR / "mount-sharp-boxwork-dem.tif"
    )
    args = parser.parse_args()
    print(json.dumps(prepare_dem(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
