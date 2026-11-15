from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS
from rasterio.errors import RasterioError


class RasterDataError(ValueError):
    """Raised when a raster cannot be safely used by the application."""


@dataclass(slots=True)
class RasterGrid:
    path: Path
    values: np.ndarray
    valid_mask: np.ndarray
    transform: Any
    crs: CRS
    nodata: float | None
    width: int
    height: int
    elevation_unit: str = "m"

    @property
    def shape(self) -> tuple[int, int]:
        return self.values.shape

    @property
    def resolution_m(self) -> tuple[float, float]:
        transform = self.transform

        column_size = float(np.hypot(transform.a, transform.d))
        row_size = float(np.hypot(transform.b, transform.e))

        return column_size, row_size

    def world_to_cell(
        self,
        x_m: float,
        y_m: float,
    ) -> tuple[int, int]:
        if not np.isfinite(x_m) or not np.isfinite(y_m):
            raise RasterDataError("Coordinates must be finite.")

        column, row = (~self.transform) * (x_m, y_m)

        row_index = int(np.floor(row))
        column_index = int(np.floor(column))

        if not (0 <= row_index < self.height and 0 <= column_index < self.width):
            raise RasterDataError("The requested coordinate is outside DEM coverage.")

        return row_index, column_index

    def cell_center(
        self,
        row: int,
        column: int,
    ) -> tuple[float, float]:
        if not (0 <= row < self.height and 0 <= column < self.width):
            raise RasterDataError("Cell lies outside the DEM.")

        x_m, y_m = self.transform * (column + 0.5, row + 0.5)

        return float(x_m), float(y_m)


def resolve_data_path(
    data_dir: Path,
    relative_path: str,
) -> Path:
    """Resolve a path while preventing access outside the data directory."""
    root = data_dir.expanduser().resolve()
    requested = Path(relative_path)

    if requested.is_absolute():
        raise ValueError("Only paths relative to the data directory are accepted.")

    resolved = (root / requested).resolve()

    if not resolved.is_relative_to(root):
        raise ValueError("The requested file must remain inside the data directory.")

    if not resolved.is_file():
        raise FileNotFoundError(f"Data file not found: {relative_path}")

    return resolved


def validate_mars_projected_crs(dataset_crs: Any) -> CRS:
    """Validate the horizontal CRS requirements of the route engine."""
    if dataset_crs is None:
        raise RasterDataError("The DEM does not declare a coordinate reference system.")

    try:
        crs = CRS.from_user_input(dataset_crs)
    except Exception as exc:
        raise RasterDataError("The raster CRS could not be interpreted.") from exc

    if not crs.is_projected:
        raise RasterDataError("The route DEM must use a projected Martian CRS.")

    axes = crs.axis_info[:2]

    if len(axes) != 2:
        raise RasterDataError("The projected CRS must define two horizontal axes.")

    if any(
        axis.unit_conversion_factor is None or not np.isclose(axis.unit_conversion_factor, 1.0)
        for axis in axes
    ):
        raise RasterDataError("The projected CRS axes must use metres.")

    ellipsoid = crs.ellipsoid

    if ellipsoid is None:
        raise RasterDataError("The projected CRS does not define an ellipsoid.")

    semi_major = ellipsoid.semi_major_metre

    if not np.isfinite(semi_major) or not (3_300_000.0 <= semi_major <= 3_500_000.0):
        raise RasterDataError(
            "The CRS ellipsoid is not compatible with the configured Martian radius range."
        )

    return crs


def _elevation_unit_factor_to_meters(unit: str | None) -> float:
    if unit is None:
        raise RasterDataError(
            "The DEM does not declare its vertical unit. "
            "Prepare the DEM in metres and set its band unit."
        )

    normalized = unit.strip().lower()

    factors = {
        "m": 1.0,
        "meter": 1.0,
        "meters": 1.0,
        "metre": 1.0,
        "metres": 1.0,
        "km": 1000.0,
        "kilometer": 1000.0,
        "kilometers": 1000.0,
        "kilometre": 1000.0,
        "kilometres": 1000.0,
    }

    try:
        return factors[normalized]
    except KeyError as exc:
        raise RasterDataError(
            f"Unsupported DEM vertical unit: {unit!r}. "
            "Convert the DEM elevations to metres before planning."
        ) from exc


def _band_scale_offset(dataset, band_index: int = 0) -> tuple[float, float]:
    scale = float(dataset.scales[band_index])
    offset = float(dataset.offsets[band_index])

    if not np.isfinite(scale) or not np.isfinite(offset):
        raise RasterDataError("Raster scale and offset must be finite.")

    return scale, offset


def inspect_raster(path: Path) -> dict[str, Any]:
    try:
        with rasterio.open(path) as dataset:
            bounds = dataset.bounds

            ellipsoid = None

            if dataset.crs is not None:
                crs = CRS.from_user_input(dataset.crs)
                crs_ellipsoid = crs.ellipsoid

                if crs_ellipsoid is not None:
                    ellipsoid = crs_ellipsoid.semi_major_metre

            scale, offset = _band_scale_offset(dataset) if dataset.count else (1.0, 0.0)

            band_unit = dataset.units[0] if dataset.count and dataset.units else None

            return {
                "file_name": path.name,
                "driver": dataset.driver,
                "width": dataset.width,
                "height": dataset.height,
                "band_count": dataset.count,
                "dtype": dataset.dtypes[0] if dataset.count else None,
                "crs": dataset.crs.to_string() if dataset.crs else None,
                "ellipsoid_semi_major_m": ellipsoid,
                "bounds": {
                    "left": float(bounds.left),
                    "bottom": float(bounds.bottom),
                    "right": float(bounds.right),
                    "top": float(bounds.top),
                },
                "nodata": (float(dataset.nodata) if dataset.nodata is not None else None),
                "resolution": [float(value) for value in dataset.res],
                "transform": [float(value) for value in list(dataset.transform)[:6]],
                "band_unit": band_unit,
                "scale": scale,
                "offset": offset,
            }

    except RasterioError as exc:
        raise RasterDataError(f"Could not inspect raster: {exc}") from exc


def read_dem(
    path: Path,
    max_cells: int = 10_000_000,
) -> RasterGrid:
    """Load one elevation band and normalize its elevations to metres."""

    if max_cells < 9:
        raise ValueError("max_cells must be at least 9.")

    try:
        with rasterio.open(path) as dataset:
            if dataset.count < 1:
                raise RasterDataError("The raster does not contain any bands.")

            if dataset.width * dataset.height > max_cells:
                raise RasterDataError(f"DEM exceeds the configured cell limit of {max_cells:,}.")

            crs = validate_mars_projected_crs(dataset.crs)

            if dataset.width < 3 or dataset.height < 3:
                raise RasterDataError("The DEM must be at least 3x3 cells.")

            transform = dataset.transform

            determinant = transform.a * transform.e - transform.b * transform.d

            if not np.isfinite(determinant) or np.isclose(
                determinant,
                0.0,
            ):
                raise RasterDataError("The raster affine transform is singular.")

            unit = dataset.units[0] if dataset.units else None

            unit_factor = _elevation_unit_factor_to_meters(unit)
            scale, offset = _band_scale_offset(dataset)

            masked = dataset.read(
                1,
                masked=True,
            )

            raw_values = np.asarray(
                masked.data,
                dtype=np.float64,
            )

            nodata_mask = np.ma.getmaskarray(masked)

            valid_mask = ~nodata_mask & np.isfinite(raw_values)

            # Convert raw stored values into physical metres.
            values = (raw_values * scale + offset) * unit_factor

            values = np.where(
                valid_mask,
                values,
                np.nan,
            )

            if not np.any(valid_mask):
                raise RasterDataError("The DEM contains no valid elevation cells.")

            return RasterGrid(
                path=path,
                values=values,
                valid_mask=valid_mask,
                transform=transform,
                crs=crs,
                nodata=dataset.nodata,
                width=dataset.width,
                height=dataset.height,
                elevation_unit="m",
            )

    except RasterioError as exc:
        raise RasterDataError(f"Could not read DEM: {exc}") from exc


def read_aligned_layer(
    path: Path,
    reference: RasterGrid,
    normalized: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Read an auxiliary raster after checking exact grid alignment."""

    try:
        with rasterio.open(path) as dataset:
            if dataset.count < 1:
                raise RasterDataError("The auxiliary raster has no bands.")

            if dataset.width != reference.width or dataset.height != reference.height:
                raise RasterDataError(f"Layer {path.name} does not match DEM dimensions.")

            layer_crs = validate_mars_projected_crs(dataset.crs)

            # Do not silently accept different CRS definitions or axis conventions.
            if layer_crs != reference.crs:
                raise RasterDataError(f"Layer {path.name} does not use the same CRS as the DEM.")

            if dataset.transform != reference.transform:
                raise RasterDataError(f"Layer {path.name} is not pixel-aligned with the DEM.")

            scale, offset = _band_scale_offset(dataset)

            masked = dataset.read(
                1,
                masked=True,
            )

            raw_values = np.asarray(
                masked.data,
                dtype=np.float64,
            )

            valid = ~np.ma.getmaskarray(masked) & np.isfinite(raw_values)

            values = raw_values * scale + offset

            values = np.where(
                valid,
                values,
                np.nan,
            )

            if normalized and np.any(valid):
                selected = values[valid]

                if np.any((selected < 0.0) | (selected > 1.0)):
                    raise RasterDataError(f"Layer {path.name} must use values in [0, 1].")

            return values, valid

    except RasterioError as exc:
        raise RasterDataError(f"Could not read auxiliary raster {path.name}: {exc}") from exc
