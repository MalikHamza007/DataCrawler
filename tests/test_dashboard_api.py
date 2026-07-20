from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_dashboard_projects_pagination_filtering_and_sorting(client):
    client.post("/api/projects", json={"name": "Alpha Heights", "lahore_zone": "Gulberg", "project_type": "apartments"})
    client.post("/api/projects", json={"name": "Beta Mall", "lahore_zone": "DHA", "project_type": "commercial"})
    response = client.get("/api/dashboard/projects", params={"q": "Alpha", "sort": "name", "direction": "asc", "limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 1
    assert data["items"][0]["name"] == "Alpha Heights"
    assert data["applied_filters"]["q"] == "Alpha"


def test_dashboard_invalid_sort_rejected(client):
    response = client.get("/api/dashboard/projects", params={"sort": "drop_table"})
    assert response.status_code == 422


def test_map_projects_validates_bounds_and_limits_payload(client):
    client.post("/api/projects", json={"name": "Mapped Heights", "latitude": 31.52, "longitude": 74.35})
    response = client.get("/api/map/projects", params={"north": 31.8, "south": 31.3, "east": 74.6, "west": 74.1, "zoom": 11})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["name"] == "Mapped Heights"
    assert "description" not in item
    bad = client.get("/api/map/projects", params={"north": 80, "south": -80, "east": 170, "west": -170, "zoom": 2})
    assert bad.status_code == 422


def test_project_review_and_version_conflict(client):
    created = client.post("/api/projects", json={"name": "Review Heights"}).json()
    response = client.post(f"/api/projects/{created['id']}/review", json={"review_status": "approved", "review_note": "Confirmed.", "expected_version": created["version_number"]})
    assert response.status_code == 200
    data = response.json()
    assert data["item"]["review_status"] == "approved"
    assert data["item"]["version_number"] == created["version_number"] + 1
    stale = client.post(f"/api/projects/{created['id']}/review", json={"review_status": "needs_review", "review_note": "stale", "expected_version": created["version_number"]})
    assert stale.status_code == 409


def test_outreach_activity_updates_project_status_and_timeline(client):
    project = client.post("/api/projects", json={"name": "Outreach Heights"}).json()
    follow_up = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    response = client.post("/api/dashboard/outreach-activities", json={"project_id": project["id"], "activity_type": "contact_attempt", "channel": "whatsapp", "direction": "outbound", "status_after": "contacted", "follow_up_at": follow_up, "note": "Manual WhatsApp sent."})
    assert response.status_code == 200
    detail = client.get(f"/api/projects/{project['id']}/dashboard-detail").json()
    assert detail["project"]["outreach_status"] == "contacted"
    assert len(detail["outreach"]) == 1


def test_bulk_action_partial_failure(client):
    active = client.post("/api/projects", json={"name": "Active Bulk"}).json()
    missing_id = active["id"] + 999
    response = client.post("/api/dashboard/bulk-actions", json={"entity_type": "project", "entity_ids": [active["id"], missing_id], "action": "set_review_status", "payload": {"review_status": "needs_review", "note": "Bulk note"}})
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 1
    assert data["failed"] == 1


def test_dashboard_summary_counts(client):
    client.post("/api/projects", json={"name": "Summary A"})
    client.post("/api/projects", json={"name": "Summary B"})
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["projects"]["total_active"] == 2

