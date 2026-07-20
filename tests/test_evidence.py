from fastapi.testclient import TestClient


def test_source_evidence(client: TestClient, developer: dict, project: dict) -> None:
    developer_evidence = client.post(
        "/api/evidence",
        json={
            "developer_id": developer["id"],
            "source_type": "official_website",
            "source_url": "https://example.com/about",
            "captured_text": "Example Developers is a Lahore builder.",
            "field_name": "developer_name",
            "extracted_value": "Example Developers",
        },
    )
    assert developer_evidence.status_code == 201
    assert developer_evidence.json()["collected_at"] is not None

    relationship = client.post(
        "/api/evidence",
        json={
            "developer_id": developer["id"],
            "project_id": project["id"],
            "source_type": "official_website",
            "source_url": "https://example.com/projects/example-heights",
            "field_name": "developer_relationship",
            "extracted_value": "Example Heights by Example Developers",
        },
    )
    assert relationship.status_code == 201

    filtered = client.get("/api/evidence", params={"source_type": "official_website"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 2


def test_evidence_requires_source_url_and_owner(client: TestClient) -> None:
    no_url = client.post("/api/evidence", json={"developer_id": 1, "source_type": "manual"})
    assert no_url.status_code == 422

    no_owner = client.post("/api/evidence", json={"source_type": "manual", "source_url": "https://example.com"})
    assert no_owner.status_code == 422
