from fastapi.testclient import TestClient

from app.core.config import get_settings


def create_job(client: TestClient) -> dict:
    response = client.post(
        "/api/collection-jobs",
        json={
            "job_type": "places_discovery",
            "city": "Lahore",
            "lahore_zone": "Gulberg",
            "search_config_json": {
                "search_mode": "zone",
                "zone_id": "gulberg",
                "radius_meters": 5000,
                "project_types": ["apartments"],
                "map_center": {"lat": 31.5106, "lng": 74.3441},
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def test_places_status_hides_server_key(monkeypatch, client: TestClient) -> None:
    monkeypatch.setenv("GOOGLE_PLACES_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_PLACES_SERVER_API_KEY", "test-secret-key")
    get_settings.cache_clear()
    try:
        response = client.get("/api/places/status")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["configured"] is True
        assert "test-secret-key" not in response.text
        assert "api_key" not in response.text
    finally:
        monkeypatch.delenv("GOOGLE_PLACES_ENABLED", raising=False)
        monkeypatch.delenv("GOOGLE_PLACES_SERVER_API_KEY", raising=False)
        get_settings.cache_clear()


def test_places_status_disabled_without_key(client: TestClient) -> None:
    response = client.get("/api/places/status")
    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_places_plan_endpoint_makes_no_google_request(client: TestClient) -> None:
    job = create_job(client)
    response = client.post(f"/api/collection-jobs/{job['id']}/places-plan")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job["id"]
    assert data["query_count"] >= 1
    assert data["cell_count"] >= 1
    assert "apartment project in Gulberg Lahore" in {query["query"] for query in data["queries"]}


def test_non_places_job_plan_is_rejected(client: TestClient) -> None:
    response = client.post("/api/collection-jobs", json={"job_type": "manual_research"})
    assert response.status_code == 201
    plan = client.post(f"/api/collection-jobs/{response.json()['id']}/places-plan")
    assert plan.status_code == 409
