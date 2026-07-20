from fastapi.testclient import TestClient

def test_map_config_returns_lahore_without_secrets(client: TestClient) -> None:
    response = client.get("/api/map-config")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Lahore"
    assert -90 <= data["default_center"]["lat"] <= 90
    assert -180 <= data["default_center"]["lng"] <= 180
    assert data["radius_options"] == [1000, 2000, 3000, 5000, 10000, 15000]
    assert {"value": "apartments", "label": "Apartments"} in data["project_types"]
    assert data["service_boundary"]["north"] == 31.75
    assert "database_url" not in data
    assert "google_maps_browser_api_key" not in data


def test_lahore_zones(client: TestClient) -> None:
    response = client.get("/api/lahore-zones")
    assert response.status_code == 200
    items = response.json()["items"]
    names = {item["name"] for item in items}
    assert "Gulberg" in names
    assert "DHA Lahore" in names
    for zone in items:
        assert -90 <= zone["center"]["lat"] <= 90
        assert -180 <= zone["center"]["lng"] <= 180
        if zone["bounds"]:
            assert zone["bounds"]["north"] > zone["bounds"]["south"]
            assert zone["bounds"]["east"] > zone["bounds"]["west"]


def test_demo_projects_endpoint_removed(client: TestClient) -> None:
    response = client.get("/api/demo-projects")
    assert response.status_code == 404
