import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from pyproj import CRS, Transformer
from rasterio.transform import from_origin

from core.config import get_settings
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("MARTIAN_MAP_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Martian Map API"


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mission_metadata() -> None:
    response = client.get("/api/mission")
    assert response.status_code == 200
    body = response.json()
    assert body["route_profiles"] == ["direct", "low_slope", "conservative"]
    assert body["planning_status"] == "not_implemented"


def test_plan_endpoint_does_not_claim_fake_route() -> None:
    response = client.post(
        "/api/mission/plan",
        json={
            "start": {"longitude": 137.4, "latitude": -4.6},
            "destination": {"longitude": 137.5, "latitude": -4.7},
            "profile": "low_slope",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_implemented"
    assert body["route"] == []
    assert body["distance_m"] is None


def test_plan_rejects_identical_coordinates() -> None:
    response = client.post(
        "/api/mission/plan",
        json={
            "start": {"longitude": 137.4, "latitude": -4.6},
            "destination": {"longitude": 137.4, "latitude": -4.6},
            "profile": "direct",
        },
    )
    assert response.status_code == 422


def test_mars_dem_profiles_and_coverage(isolated_data_dir) -> None:
    crs = CRS.from_user_input("ESRI:103885")
    transform = from_origin(8_143_000, -285_000, 1, 1)
    to_mars = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
    path = isolated_data_dir / "mount-sharp-boxwork-dem.tif"
    elevations = np.zeros((7, 7), dtype="float32")
    elevations[3, 3] = 30

    def write_dem() -> None:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=7,
            width=7,
            count=1,
            dtype="float32",
            nodata=-9999,
            crs=crs.to_wkt(),
            transform=transform,
        ) as dem:
            dem.write(elevations, 1)

    def point(x, y):
        longitude, latitude = to_mars.transform(x, y)
        return {"latitude": latitude, "longitude": longitude}

    write_dem()
    start = point(*(transform @ (1.5, 3.5)))
    destination = point(*(transform @ (5.5, 3.5)))
    payload = {"start": start, "destination": destination}
    assert client.get("/api/mission").json()["planning_status"] == "ready"

    direct = client.post(
        "/api/mission/plan", json={**payload, "profile": "direct"}
    ).json()
    gentle = client.post(
        "/api/mission/plan", json={**payload, "profile": "low_slope"}
    ).json()
    assert direct["status"] == gentle["status"] == "planned"
    assert direct["route"][0] == start and gentle["route"][-1] == destination
    assert point(*(transform @ (3.5, 3.5))) in direct["route"]
    assert point(*(transform @ (3.5, 3.5))) not in gentle["route"]
    assert gentle["distance_m"] > direct["distance_m"]

    outside = client.post(
        "/api/mission/plan",
        json={**payload, "destination": point(*(transform @ (9.5, 3.5)))},
    ).json()
    assert outside["status"] == "outside_coverage" and outside["route"] == []

    elevations[:, 3] = -9999
    write_dem()
    blocked = client.post("/api/mission/plan", json=payload).json()
    assert blocked["status"] == "no_path" and blocked["route"] == []
