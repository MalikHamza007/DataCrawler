from fastapi.testclient import TestClient


def test_developer_crud_and_normalization(client: TestClient) -> None:
    create_response = client.post("/api/developers", json={"name": "  ABS Developers (Pvt.) Ltd. "})
    assert create_response.status_code == 201
    developer = create_response.json()
    assert developer["normalized_name"] == "abs developers pvt ltd"

    get_response = client.get(f"/api/developers/{developer['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "  ABS Developers (Pvt.) Ltd. "

    list_response = client.get("/api/developers", params={"name": "abs developers"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.patch(f"/api/developers/{developer['id']}", json={"name": "ABS Builders"})
    assert update_response.status_code == 200
    assert update_response.json()["normalized_name"] == "abs builders"

    delete_response = client.delete(f"/api/developers/{developer['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/developers/{developer['id']}").status_code == 404


def test_missing_developer_returns_404(client: TestClient) -> None:
    response = client.get("/api/developers/999")
    assert response.status_code == 404


def test_developer_with_multiple_projects(client: TestClient, developer: dict) -> None:
    for name in ["Example Heights", "Example Business Square"]:
        response = client.post("/api/projects", json={"name": name, "developer_id": developer["id"]})
        assert response.status_code == 201

    response = client.get(f"/api/developers/{developer['id']}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["projects"]) == 2
