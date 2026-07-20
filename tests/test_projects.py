from fastapi.testclient import TestClient


def test_project_without_and_with_developer(client: TestClient, developer: dict) -> None:
    unassigned = client.post("/api/projects", json={"name": "Unknown Residences", "lahore_zone": "Raiwind Road"})
    assert unassigned.status_code == 201
    assert unassigned.json()["developer_id"] is None

    assigned = client.post("/api/projects", json={"name": "Example Heights", "developer_id": developer["id"]})
    assert assigned.status_code == 201
    assert assigned.json()["developer_id"] == developer["id"]


def test_assign_and_remove_developer(client: TestClient, developer: dict, project: dict) -> None:
    assign = client.patch(f"/api/projects/{project['id']}/developer", json={"developer_id": developer["id"]})
    assert assign.status_code == 200
    assert assign.json()["developer_id"] == developer["id"]

    remove = client.patch(f"/api/projects/{project['id']}/developer", json={"developer_id": None})
    assert remove.status_code == 200
    assert remove.json()["developer_id"] is None


def test_project_filters_and_duplicate_google_place_id(client: TestClient, developer: dict) -> None:
    first = client.post(
        "/api/projects",
        json={"name": "Example Heights", "developer_id": developer["id"], "lahore_zone": "Gulberg", "google_place_id": "abc123"},
    )
    assert first.status_code == 201
    second = client.post("/api/projects", json={"name": "Duplicate Heights", "google_place_id": "abc123"})
    assert second.status_code == 409

    by_developer = client.get("/api/projects", params={"developer_id": developer["id"]})
    assert by_developer.status_code == 200
    assert len(by_developer.json()) == 1

    by_zone = client.get("/api/projects", params={"lahore_zone": "Gulberg"})
    assert by_zone.status_code == 200
    assert len(by_zone.json()) == 1


def test_latitude_and_longitude_validation(client: TestClient) -> None:
    bad_latitude = client.post("/api/projects", json={"name": "Bad Lat", "latitude": 91})
    assert bad_latitude.status_code == 422

    bad_longitude = client.post("/api/projects", json={"name": "Bad Lng", "longitude": 181})
    assert bad_longitude.status_code == 422


def test_delete_developer_does_not_delete_projects(client: TestClient, developer: dict) -> None:
    project_response = client.post("/api/projects", json={"name": "Persistent Project", "developer_id": developer["id"]})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    delete_response = client.delete(f"/api/developers/{developer['id']}")
    assert delete_response.status_code == 204

    project_after = client.get(f"/api/projects/{project_id}")
    assert project_after.status_code == 200
    assert project_after.json()["developer_id"] is None
