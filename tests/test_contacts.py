from fastapi.testclient import TestClient


def test_developer_and_project_contacts(client: TestClient, developer: dict, project: dict) -> None:
    developer_contact = client.post(
        "/api/contacts",
        json={"developer_id": developer["id"], "contact_type": "phone", "value": "0300 1234567"},
    )
    assert developer_contact.status_code == 201
    assert developer_contact.json()["normalized_value"] == "03001234567"

    project_contact = client.post(
        "/api/contacts",
        json={"project_id": project["id"], "contact_type": "email", "value": "SALES@EXAMPLE.COM"},
    )
    assert project_contact.status_code == 201
    assert project_contact.json()["normalized_value"] == "sales@example.com"


def test_invalid_contact_ownership(client: TestClient, developer: dict, project: dict) -> None:
    both = client.post(
        "/api/contacts",
        json={"developer_id": developer["id"], "project_id": project["id"], "contact_type": "phone", "value": "03001234567"},
    )
    assert both.status_code == 422

    neither = client.post("/api/contacts", json={"contact_type": "phone", "value": "03001234567"})
    assert neither.status_code == 422


def test_contact_missing_owner_update_delete(client: TestClient) -> None:
    missing = client.post("/api/contacts", json={"developer_id": 999, "contact_type": "phone", "value": "03001234567"})
    assert missing.status_code == 404

    developer = client.post("/api/developers", json={"name": "Contact Dev"}).json()
    contact = client.post("/api/contacts", json={"developer_id": developer["id"], "contact_type": "phone", "value": "03001234567"}).json()

    update = client.patch(f"/api/contacts/{contact['id']}", json={"value": "0300 7654321"})
    assert update.status_code == 200
    assert update.json()["normalized_value"] == "03007654321"

    delete = client.delete(f"/api/contacts/{contact['id']}")
    assert delete.status_code == 204
    assert client.get(f"/api/contacts/{contact['id']}").status_code == 404
