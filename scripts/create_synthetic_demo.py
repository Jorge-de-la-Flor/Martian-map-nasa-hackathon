from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "demo"

CRS_MARS = CRS.from_proj4(
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

SIZE = 121
CELL_SIZE_M = 100.0
CENTER = SIZE // 2

TRANSFORM = from_origin(
    -CENTER * CELL_SIZE_M - CELL_SIZE_M / 2,
    CENTER * CELL_SIZE_M + CELL_SIZE_M / 2,
    CELL_SIZE_M,
    CELL_SIZE_M,
)


def save_raster(
    path: Path,
    values: np.ndarray,
    unit: str,
) -> None:
    """Save a synthetic single-band Martian GeoTIFF."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = np.asarray(
        values,
        dtype=np.float32,
    )

    if data.shape != (SIZE, SIZE):
        raise ValueError(f"Expected raster shape {(SIZE, SIZE)}, got {data.shape}.")

    if unit not in {"m", "1"}:
        raise ValueError("Synthetic raster unit must be 'm' or '1'.")

    if not np.all(np.isfinite(data)):
        raise ValueError("Synthetic demonstration rasters must contain finite values.")

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=SIZE,
        width=SIZE,
        count=1,
        dtype="float32",
        crs=CRS_MARS.to_wkt(),
        transform=TRANSFORM,
        nodata=-9999.0,
        compress="deflate",
    ) as dataset:
        dataset.write(data, 1)
        dataset.set_band_unit(1, unit)


def main() -> None:
    rows, columns = np.indices((SIZE, SIZE))

    x = (columns - CENTER) * CELL_SIZE_M
    y = (CENTER - rows) * CELL_SIZE_M

    ridge = 180.0 * np.exp(-((x / 400.0) ** 2)) * np.exp(-((y / 1300.0) ** 2))

    regional_gradient = 0.01 * x + 0.005 * y

    elevation = 1200.0 + regional_gradient + ridge

    hazard = np.zeros(
        (SIZE, SIZE),
        dtype=np.float32,
    )

    hazard[45:76, 56:65] = 1.0

    uncertainty = np.zeros(
        (SIZE, SIZE),
        dtype=np.float32,
    )

    uncertainty[35:80, 43:51] = 0.8

    save_raster(
        OUTPUT / "synthetic_dem.tif",
        elevation,
        "m",
    )

    save_raster(
        OUTPUT / "synthetic_hazard.tif",
        hazard,
        "1",
    )

    save_raster(
        OUTPUT / "synthetic_uncertainty.tif",
        uncertainty,
        "1",
    )

    start_x, start_y = TRANSFORM * (20.5, 60.5)
    destination_x, destination_y = TRANSFORM * (100.5, 60.5)

    print("Synthetic Martian terrain created.")
    print(f"Directory: {OUTPUT}")
    print("DEM: data/demo/synthetic_dem.tif")
    print("Hazard: data/demo/synthetic_hazard.tif")
    print("Uncertainty: data/demo/synthetic_uncertainty.tif")
    print()
    print("Start:")
    print(f"  x_m={start_x}")
    print(f"  y_m={start_y}")
    print()
    print("Destination:")
    print(f"  x_m={destination_x}")
    print(f"  y_m={destination_y}")
    print()
    print("WARNING: These are synthetic data, not NASA observations.")


if __name__ == "__main__":
    main()
