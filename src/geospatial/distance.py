from math import asin, cos, radians, sin, sqrt

MARS_MEAN_RADIUS_M = 3_389_500.0


def haversine_distance_m(
    latitude_a_deg: float,
    longitude_a_deg: float,
    latitude_b_deg: float,
    longitude_b_deg: float,
    radius_m: float = MARS_MEAN_RADIUS_M,
) -> float:
    """
    Estimate spherical surface distance on Mars.

    Coordinates must use the same planetary latitude and longitude
    convention. This is a spherical approximation, not an ellipsoidal
    geodesic solution.
    """
    for latitude in (latitude_a_deg, latitude_b_deg):
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees.")

    for longitude in (longitude_a_deg, longitude_b_deg):
        if not -180.0 <= longitude <= 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees.")

    if radius_m <= 0:
        raise ValueError("Planetary radius must be positive.")

    latitude_a = radians(latitude_a_deg)
    latitude_b = radians(latitude_b_deg)

    delta_latitude = latitude_b - latitude_a
    delta_longitude = radians(longitude_b_deg - longitude_a_deg)

    a = (
        sin(delta_latitude / 2.0) ** 2
        + cos(latitude_a) * cos(latitude_b) * sin(delta_longitude / 2.0) ** 2
    )

    a = min(1.0, max(0.0, a))
    central_angle = 2.0 * asin(sqrt(a))

    return radius_m * central_angle
