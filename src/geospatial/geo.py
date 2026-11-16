"""Conversión entre longitud/latitud (grados) y metros proyectados del DEM."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import rasterio
from pyproj import CRS, Transformer


@dataclass(frozen=True, slots=True)
class DemGeoreference:
    crs: CRS
    to_projected: Transformer
    to_geographic: Transformer
    west: float
    south: float
    east: float
    north: float


def load_georeference(path: Path) -> DemGeoreference:
    """Lee la proyección del DEM y prepara las conversiones en ambos sentidos."""
    with rasterio.open(path) as dataset:
        if dataset.crs is None:
            raise ValueError("The DEM does not declare a coordinate reference system.")
        crs = CRS.from_wkt(dataset.crs.to_wkt())
        bounds = dataset.bounds

    to_projected = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    to_geographic = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)

    lons, lats = to_geographic.transform(
        [bounds.left, bounds.right, bounds.left, bounds.right],
        [bounds.bottom, bounds.bottom, bounds.top, bounds.top],
    )

    return DemGeoreference(
        crs=crs,
        to_projected=to_projected,
        to_geographic=to_geographic,
        west=float(min(lons)),
        south=float(min(lats)),
        east=float(max(lons)),
        north=float(max(lats)),
    )