"""Prepare the Mount Sharp slope and profile web data from the local Gale DEM."""

import json
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import ColorInterp
from rasterio.io import MemoryFile
from rasterio.shutil import copy as copy_raster

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEM_SOURCE = "https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m"
LEGEND = [
    {"from_deg": 0, "label": "0–5°", "color": "#344d67"},
    {"from_deg": 5, "label": "5–10°", "color": "#65a39e"},
    {"from_deg": 10, "label": "10–20°", "color": "#e8bb69"},
    {"from_deg": 20, "label": "20° and above", "color": "#e46549"},
]


def slope_degrees(
    elevation: np.ndarray, east_step: np.ndarray, north_step: float
) -> np.ndarray:
    center = elevation[1:-1, 1:-1]
    east = (elevation[1:-1, 2:] - elevation[1:-1, :-2]) / (2 * east_step[1:-1, None])
    north = (elevation[:-2, 1:-1] - elevation[2:, 1:-1]) / (2 * north_step)
    slope = np.full(elevation.shape, np.nan, dtype="float32")
    slope[1:-1, 1:-1] = np.where(
        np.isfinite(center), np.degrees(np.arctan(np.hypot(east, north))), np.nan
    )
    return slope


def make_profile(dem, points, to_mars, geodesic) -> dict:
    start, end = np.asarray(points)
    longitude, latitude = to_mars.transform(*np.array([start, end]).T)
    _, _, length_m = geodesic.inv(longitude[0], latitude[0], longitude[1], latitude[1])
    if length_m <= 0:
        raise ValueError("The profile needs two distinct waypoints.")
    xy = np.linspace(start, end, ceil(length_m / min(dem.res)) + 1)
    longitude, latitude = to_mars.transform(*xy.T)
    _, _, steps = geodesic.inv(
        longitude[:-1], latitude[:-1], longitude[1:], latitude[1:]
    )
    distance = np.r_[0, steps.cumsum()]
    heights = [
        float(value[0])
        if not np.ma.is_masked(value[0]) and np.isfinite(value[0])
        else None
        for value in dem.sample(xy, masked=True)
    ]
    complete = all(height is not None for height in heights)
    changes = np.diff(heights) if complete else None
    return {
        "label": "Straight reference transect",
        "distance_m": round(float(distance[-1]), 3),
        "ascent_m": round(float(np.maximum(changes, 0).sum()), 3) if complete else None,
        "descent_m": round(float(np.maximum(-changes, 0).sum()), 3)
        if complete
        else None,
        "samples": [
            {
                "distance_m": round(float(d), 3),
                "elevation_m": round(h, 3) if h is not None else None,
            }
            for d, h in zip(distance, heights, strict=True)
        ],
    }


def write_slope(slope: np.ndarray, profile: dict, output_dir: Path) -> None:
    valid = np.isfinite(slope)
    nodata = -9999.0
    profile.update(dtype="float32", nodata=nodata)
    with rasterio.open(output_dir / "slope.tif", "w", **profile) as raster:
        raster.write(np.where(valid, slope, nodata), 1)
        raster.set_band_unit(1, "degree")

    rgba = np.zeros((4, *slope.shape), dtype="uint8")
    classes = (
        np.searchsorted([entry["from_deg"] for entry in LEGEND], slope, side="right")
        - 1
    )
    for index, entry in enumerate(LEGEND):
        color = np.frombuffer(bytes.fromhex(entry["color"][1:]), dtype="uint8")
        mask = valid & (classes == index)
        rgba[:3, mask] = color[:, None]
        rgba[3, mask] = 255
    with (
        rasterio.Env(GDAL_PAM_ENABLED="NO"),
        MemoryFile() as memory,
        memory.open(
            driver="GTiff",
            dtype="uint8",
            count=4,
            height=slope.shape[0],
            width=slope.shape[1],
            transform=profile["transform"],
            crs=profile["crs"],
        ) as raster,
    ):
        raster.colorinterp = (
            ColorInterp.red,
            ColorInterp.green,
            ColorInterp.blue,
            ColorInterp.alpha,
        )
        raster.write(rgba)
        copy_raster(raster, output_dir / "slope.png", driver="PNG")


def build(data_dir: Path) -> dict:
    catalog = json.loads(
        (data_dir / "mount-sharp-boxwork-sites.json").read_text(encoding="utf-8")
    )
    with rasterio.open(data_dir / "mount-sharp-boxwork-dem.tif") as dem:
        crs = CRS.from_user_input("ESRI:103885")
        if (
            dem.crs != crs
            or not dem.transform.is_rectilinear
            or dem.transform.a <= 0
            or dem.transform.e >= 0
        ):
            raise ValueError("Expected a north-up Gale DEM in ESRI:103885.")
        to_grid = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
        to_mars = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
        points = [
            to_grid.transform(site["longitude"], site["latitude"], errcheck=True)
            for site in catalog["sites"]
        ]
        elevation = dem.read(1, masked=True).astype("float64").filled(np.nan)
        for x, y in points:
            row, col = dem.index(x, y)
            if not (
                0 <= row < dem.height
                and 0 <= col < dem.width
                and np.isfinite(elevation[row, col])
            ):
                raise ValueError(
                    "A Curiosity waypoint falls outside valid DEM coverage."
                )
        west, south = to_mars.transform(dem.bounds.left, dem.bounds.bottom)
        east, north = to_mars.transform(dem.bounds.right, dem.bounds.top)
        latitudes = north - (np.arange(dem.height) + 0.5) * (north - south) / dem.height
        east_step = dem.res[0] * np.cos(np.radians(latitudes))
        slope = slope_degrees(elevation, east_step, dem.res[1])
        profile = make_profile(dem, points, to_mars, crs.get_geod())
        raster_profile = dem.profile
        summary = {
            **catalog,
            "dem_source": DEM_SOURCE,
            "dem_credit": "Calef III and Parker (2016), NASA/JPL and USGS Astrogeology",
            "slope": {
                "bounds_mars_degrees": {
                    "west": west,
                    "south": south,
                    "east": east,
                    "north": north,
                },
                "shape": {"width": dem.width, "height": dem.height},
                "valid_cells": int(np.isfinite(slope).sum()),
                "legend": LEGEND,
            },
            "profile": profile,
        }
    output_dir = data_dir / "boxwork"
    output_dir.mkdir(exist_ok=True)
    # Generate all outputs before replacing the existing files.
    with TemporaryDirectory(dir=data_dir) as staging:
        temp_dir = Path(staging)
        write_slope(slope, raster_profile, temp_dir)
        (temp_dir / "analysis.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        for filename in ("slope.tif", "slope.png", "analysis.json"):
            (temp_dir / filename).replace(output_dir / filename)
    return summary


if __name__ == "__main__":
    result = build(DATA_DIR)
    profile = result["profile"]
    print(
        f"Wrote data/boxwork with {result['slope']['valid_cells']:,} slope cells "
        f"and {len(profile['samples'])} profile samples over {profile['distance_m']:.2f} m."
    )
