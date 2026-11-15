from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


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
