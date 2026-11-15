import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pyproj import CRS

from api.routes import mission as mission_routes
from core.config import Settings
from main import app
from services.planner import RoutePlanner
from tests.helpers import write_raster


@pytest.fixture
def api_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    settings = Settings(data_dir=tmp_path)

    monkeypatch.setattr(
        mission_routes,
        "settings",
        settings,
    )

    monkeypatch.setattr(
        mission_routes,
        "planner",
        RoutePlanner(tmp_path),
    )

    with TestClient(app) as client:
        yield client, tmp_path


def cell_center(transform, row: int, column: int):
    return transform * (
        column + 0.5,
        row + 0.5,
    )


def test_root_endpoint(api_context) -> None:
    client, _ = api_context

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["name"] == "Martian Map API"


def test_health_endpoint(api_context) -> None:
    client, _ = api_context

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mission_reports_pending_datasets(api_context) -> None:
    client, _ = api_context

    response = client.get("/api/mission")

    assert response.status_code == 200
    assert response.json()["planning_status"] == "awaiting_data"
    assert response.json()["region_name"] is None


def test_missing_catalog_returns_empty_result(api_context) -> None:
    client, _ = api_context

    response = client.get("/api/mission/layers")

    assert response.status_code == 200
    assert response.json()["region_status"] == "not_selected"
    assert response.json()["layers"] == []
    assert response.json()["available_categories"] == []


def test_catalog_marks_missing_files_as_unavailable(
    api_context,
) -> None:
    client, data_dir = api_context

    catalog = {
        "schema_version": 1,
        "region": None,
        "layers": [
            {
                "id": "missing_dem",
                "name": "DEM not downloaded",
                "category": "topographic",
                "mission": "Synthetic",
                "instrument": "Test",
                "source_url": "https://example.org/",
                "role": "route_dem",
                "resolution_m": 20.0,
                "local_path": "missing_dem.tif",
                "notes": "Product not downloaded.",
            }
        ],
    }

    (data_dir / "catalog.json").write_text(
        json.dumps(catalog),
        encoding="utf-8",
    )

    response = client.get("/api/mission/layers")

    assert response.status_code == 200

    layer = response.json()["layers"][0]

    assert layer["available"] is False
    assert layer["asset_url"] is None
    assert response.json()["available_categories"] == []


def test_raster_endpoint_returns_metadata(
    api_context,
    mars_crs: CRS,
    mars_transform,
) -> None:
    client, data_dir = api_context

    values = np.full(
        (9, 9),
        100.0,
        dtype=np.float32,
    )

    write_raster(
        data_dir / "small_dem.tif",
        values,
        mars_crs,
        mars_transform,
    )

    response = client.get(
        "/api/mission/raster",
        params={"path": "small_dem.tif"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["width"] == 9
    assert body["height"] == 9
    assert body["band_count"] == 1

    assert body["ellipsoid_semi_major_m"] == pytest.approx(
        3_396_190.0,
        abs=1.0,
    )


def test_elevation_endpoint(
    api_context,
    mars_crs: CRS,
    mars_transform,
) -> None:
    client, data_dir = api_context

    values = np.full(
        (41, 41),
        750.0,
        dtype=np.float32,
    )

    write_raster(
        data_dir / "dem.tif",
        values,
        mars_crs,
        mars_transform,
    )

    x_m, y_m = cell_center(
        mars_transform,
        20,
        20,
    )

    response = client.get(
        "/api/mission/elevation",
        params={
            "dem_path": "dem.tif",
            "x_m": x_m,
            "y_m": y_m,
        },
    )

    assert response.status_code == 200
    assert response.json()["elevation_m"] == pytest.approx(750.0)
    assert response.json()["slope_deg"] == pytest.approx(0.0)


def test_plan_endpoint_computes_a_route(
    api_context,
    mars_crs: CRS,
    mars_transform,
) -> None:
    client, data_dir = api_context

    values = np.full(
        (41, 41),
        1000.0,
        dtype=np.float32,
    )

    write_raster(
        data_dir / "dem.tif",
        values,
        mars_crs,
        mars_transform,
    )

    start_x, start_y = cell_center(
        mars_transform,
        20,
        5,
    )

    destination_x, destination_y = cell_center(
        mars_transform,
        20,
        35,
    )

    response = client.post(
        "/api/mission/plan",
        json={
            "dem_path": "dem.tif",
            "start": {
                "x_m": start_x,
                "y_m": start_y,
            },
            "destination": {
                "x_m": destination_x,
                "y_m": destination_y,
            },
            "profile": "direct",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "planned"
    assert body["profile"] == "direct"
    assert body["metrics"]["distance_m"] == pytest.approx(300.0)
    assert len(body["route"]) >= 2


def test_plan_rejects_identical_cells(
    api_context,
    mars_crs: CRS,
    mars_transform,
) -> None:
    client, data_dir = api_context

    values = np.full(
        (41, 41),
        1000.0,
        dtype=np.float32,
    )

    write_raster(
        data_dir / "dem.tif",
        values,
        mars_crs,
        mars_transform,
    )

    x_m, y_m = cell_center(
        mars_transform,
        20,
        20,
    )

    response = client.post(
        "/api/mission/plan",
        json={
            "dem_path": "dem.tif",
            "start": {
                "x_m": x_m,
                "y_m": y_m,
            },
            "destination": {
                "x_m": x_m,
                "y_m": y_m,
            },
            "profile": "direct",
        },
    )

    assert response.status_code == 422


def test_raster_endpoint_rejects_path_traversal(api_context) -> None:
    client, _ = api_context

    response = client.get(
        "/api/mission/raster",
        params={"path": "../outside.tif"},
    )

    assert response.status_code == 422


def test_registered_layer_can_be_downloaded(
    api_context,
    mars_crs: CRS,
    mars_transform,
) -> None:
    client, data_dir = api_context

    values = np.full(
        (9, 9),
        100.0,
        dtype=np.float32,
    )

    write_raster(
        data_dir / "route_dem.tif",
        values,
        mars_crs,
        mars_transform,
    )

    catalog = {
        "schema_version": 1,
        "region": {
            "name": "Synthetic Test Area",
        },
        "layers": [
            {
                "id": "test_dem",
                "name": "Synthetic DEM",
                "category": "topographic",
                "mission": "Synthetic",
                "instrument": "Test",
                "source_url": "https://example.org/",
                "role": "route_dem",
                "resolution_m": 10.0,
                "local_path": "route_dem.tif",
                "notes": "Synthetic test product.",
            }
        ],
    }

    (data_dir / "catalog.json").write_text(
        json.dumps(catalog),
        encoding="utf-8",
    )

    layers_response = client.get("/api/mission/layers")

    assert layers_response.status_code == 200

    layer = layers_response.json()["layers"][0]

    assert layer["available"] is True
    assert layer["asset_url"] == "/api/mission/layers/test_dem/file"

    file_response = client.get(
        "/api/mission/layers/test_dem/file",
    )

    assert file_response.status_code == 200
    assert len(file_response.content) > 0
