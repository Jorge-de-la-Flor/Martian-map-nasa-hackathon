import math

import pytest

from geospatial.distance import (
    MARS_MEAN_RADIUS_M,
    haversine_distance_m,
)


def test_haversine_zero_distance() -> None:
    distance = haversine_distance_m(0, 0, 0, 0)

    assert distance == pytest.approx(0.0)


def test_haversine_quarter_circumference() -> None:
    distance = haversine_distance_m(0, 0, 0, 90)

    expected = math.pi * MARS_MEAN_RADIUS_M / 2.0

    assert distance == pytest.approx(expected)


def test_haversine_rejects_invalid_latitude() -> None:
    with pytest.raises(ValueError):
        haversine_distance_m(91, 0, 0, 0)
