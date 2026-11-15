import numpy as np

from geospatial.raster import RasterGrid


def calculate_slope(dem: RasterGrid) -> np.ndarray:
    """
    Calculate terrain slope in degrees using the Horn 3x3 operator.

    Cells without a complete valid 3x3 neighborhood return NaN.
    """
    z = dem.values
    valid = dem.valid_mask

    height, width = z.shape
    slope = np.full((height, width), np.nan, dtype=np.float64)

    if height < 3 or width < 3:
        return slope

    neighbors = [
        valid[:-2, :-2],
        valid[:-2, 1:-1],
        valid[:-2, 2:],
        valid[1:-1, :-2],
        valid[1:-1, 1:-1],
        valid[1:-1, 2:],
        valid[2:, :-2],
        valid[2:, 1:-1],
        valid[2:, 2:],
    ]

    valid_windows = np.logical_and.reduce(neighbors)

    z00 = z[:-2, :-2]
    z01 = z[:-2, 1:-1]
    z02 = z[:-2, 2:]

    z10 = z[1:-1, :-2]
    z12 = z[1:-1, 2:]

    z20 = z[2:, :-2]
    z21 = z[2:, 1:-1]
    z22 = z[2:, 2:]

    dz_dcolumn = ((z02 + 2.0 * z12 + z22) - (z00 + 2.0 * z10 + z20)) / 8.0

    dz_drow = ((z20 + 2.0 * z21 + z22) - (z00 + 2.0 * z01 + z02)) / 8.0

    transform = dem.transform

    a = transform.a
    b = transform.b
    d = transform.d
    e = transform.e

    determinant = a * e - b * d

    if np.isclose(determinant, 0.0):
        raise ValueError("Cannot calculate slope with a singular affine transform.")

    # Convert pixel-coordinate derivatives into projected-coordinate derivatives.
    dz_dx = (e * dz_dcolumn - d * dz_drow) / determinant
    dz_dy = (-b * dz_dcolumn + a * dz_drow) / determinant

    gradient_magnitude = np.hypot(dz_dx, dz_dy)
    slope_inner = np.degrees(np.arctan(gradient_magnitude))

    inner = slope[1:-1, 1:-1]
    inner[valid_windows] = slope_inner[valid_windows]

    return slope
