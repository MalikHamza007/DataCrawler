from fastapi.testclient import TestClient


def test_collection_job_creation_transition_log_and_delete(client: TestClient) -> None:
    create = client.post(
        "/api/collection-jobs",
        json={"job_type": "manual_research", "lahore_zone": "Gulberg", "search_config_json": {"city": "Lahore"}},
    )
    assert create.status_code == 201
    job = create.json()
    assert job["status"] == "queued"

    get_response = client.get(f"/api/collection-jobs/{job['id']}")
    assert get_response.status_code == 200

    filtered = client.get("/api/collection-jobs", params={"status": "queued"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    invalid = client.patch(f"/api/collection-jobs/{job['id']}", json={"status": "completed"})
    assert invalid.status_code == 409

    running = client.patch(f"/api/collection-jobs/{job['id']}", json={"status": "running"})
    assert running.status_code == 200
    assert running.json()["status"] == "running"
    assert running.json()["started_at"] is not None

    log = client.post(f"/api/collection-jobs/{job['id']}/logs", json={"level": "info", "message": "Started"})
    assert log.status_code == 201
    assert log.json()["collection_job_id"] == job["id"]

    completed = client.patch(f"/api/collection-jobs/{job['id']}", json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None

    delete = client.delete(f"/api/collection-jobs/{job['id']}")
    assert delete.status_code == 204
    assert client.get(f"/api/collection-jobs/{job['id']}").status_code == 404


def test_reject_invalid_collection_job_status(client: TestClient) -> None:
    response = client.post("/api/collection-jobs", json={"job_type": "manual_research"})
    assert response.status_code == 201
    job = response.json()

    invalid = client.patch(f"/api/collection-jobs/{job['id']}", json={"status": "paused"})
    assert invalid.status_code == 422
