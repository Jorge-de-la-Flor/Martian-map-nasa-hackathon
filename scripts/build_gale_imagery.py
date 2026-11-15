"""Prepare token-free regional and local views from the USGS Gale color mosaic."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import ColorInterp, Resampling
from rasterio.io import MemoryFile
from rasterio.shutil import copy as copy_raster
from rasterio.transform import from_origin
from rasterio.windows import Window, bounds, from_bounds

DATA = Path(__file__).resolve().parents[1] / "data"
SOURCE = (
    "https://asc-pds-services.s3.us-west-2.amazonaws.com/"
    "mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.tif"
)
CTX_TILES = "https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0/default/default028mm"


def build_ctx_context(output: Path) -> dict:
    level, first_col, first_row = 10, 1804, 537
    tile_size, count = 256, 3
    mosaic = np.empty((2, tile_size * count, tile_size * count), dtype="uint8")
    cells = [(row, col) for row in range(count) for col in range(count)]
    with httpx.Client(timeout=20, follow_redirects=True) as client:

        def fetch(cell):
            row, col = cell
            response = client.get(
                f"{CTX_TILES}/{level}/{first_row + row}/{first_col + col}.png"
            )
            response.raise_for_status()
            with MemoryFile(response.content) as memory, memory.open() as tile:
                return tile.read()

        with ThreadPoolExecutor(max_workers=4) as pool:
            for (row, col), tile in zip(cells, pool.map(fetch, cells), strict=True):
                r, c = row * tile_size, col * tile_size
                mosaic[:, r : r + tile_size, c : c + tile_size] = tile
    tile_degrees = 180 / (2**level)
    west, north = -180 + first_col * tile_degrees, 90 - first_row * tile_degrees
    transform = from_origin(
        west, north, tile_degrees / tile_size, tile_degrees / tile_size
    )
    with (
        MemoryFile() as memory,
        memory.open(
            driver="GTiff",
            width=mosaic.shape[2],
            height=mosaic.shape[1],
            count=2,
            dtype="uint8",
            transform=transform,
        ) as raster,
    ):
        raster.colorinterp = (ColorInterp.gray, ColorInterp.alpha)
        raster.write(mosaic)
        copy_raster(raster, output / "gale-context.png", driver="PNG")
    return {
        "west": west,
        "north": north,
        "east": west + count * tile_degrees,
        "south": north - count * tile_degrees,
    }


def build() -> None:
    with rasterio.open(DATA / "mount-sharp-boxwork-dem.tif") as dem:
        extent = dem.bounds
        crs = CRS.from_wkt(dem.crs.to_wkt())
    to_mars = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
    output = DATA / "boxwork"
    output.mkdir(exist_ok=True)
    with (
        TemporaryDirectory(dir=output) as folder,
        rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="30"),
        rasterio.open(SOURCE) as image,
    ):
        temporary = Path(folder)
        regional = Window(0, 0, image.width, image.height)
        local = (
            from_bounds(*extent, transform=image.transform)
            .round_offsets()
            .round_lengths()
        )
        manifest = {"gale-context": build_ctx_context(temporary)}
        for name, window, size in (
            ("gale", regional, 1600),
            ("mount-sharp", local, 1024),
        ):
            ratio = size / max(window.width, window.height)
            width, height = round(window.width * ratio), round(window.height * ratio)
            colors = image.read(
                window=window,
                out_shape=(3, height, width),
                resampling=Resampling.average,
                masked=True,
            )
            alpha = np.where(np.ma.getmaskarray(colors).any(axis=0), 0, 255).astype(
                "uint8"
            )
            rgba = np.concatenate((colors.filled(0), alpha[None]))
            with (
                MemoryFile() as memory,
                memory.open(
                    driver="GTiff",
                    width=width,
                    height=height,
                    count=4,
                    dtype="uint8",
                    transform=image.window_transform(window),
                ) as raster,
            ):
                raster.colorinterp = (
                    ColorInterp.red,
                    ColorInterp.green,
                    ColorInterp.blue,
                    ColorInterp.alpha,
                )
                raster.write(rgba)
                copy_raster(raster, temporary / f"{name}.png", driver="PNG")
            left, bottom, right, top = bounds(window, image.transform)
            west, south = to_mars.transform(left, bottom)
            east, north = to_mars.transform(right, top)
            manifest[name] = {
                "west": west,
                "south": south,
                "east": east,
                "north": north,
            }
        for name in manifest:
            (temporary / f"{name}.png").replace(output / f"{name}.png")
        (temporary / "imagery.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        (temporary / "imagery.json").replace(output / "imagery.json")


if __name__ == "__main__":
    build()
