from fastapi.testclient import TestClient


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


def test_cancel_retry_and_logs_api(client: TestClient) -> None:
    job = create_job(client)
    cancel = client.post(f"/api/collection-jobs/{job['id']}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert cancel.json()["progress_phase"] == "cancelled"

    retry = client.post(f"/api/collection-jobs/{job['id']}/retry")
    assert retry.status_code == 200
    assert retry.json()["status"] == "queued"

    logs = client.get(f"/api/collection-jobs/{job['id']}/logs")
    assert logs.status_code == 200
    assert len(logs.json()) >= 2


def test_cancel_terminal_and_retry_running_rejected(client: TestClient) -> None:
    job = create_job(client)
    assert client.post(f"/api/collection-jobs/{job['id']}/cancel").status_code == 200
    assert client.post(f"/api/collection-jobs/{job['id']}/cancel").status_code == 409

    running = create_job(client)
    # PATCH remains a test helper for state transition; normal collection still requires the worker.
    assert client.patch(f"/api/collection-jobs/{running['id']}", json={"status": "running"}).status_code == 200
    assert client.post(f"/api/collection-jobs/{running['id']}/retry").status_code == 409
