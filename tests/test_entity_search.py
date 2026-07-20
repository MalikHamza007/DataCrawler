from __future__ import annotations

from app.db.session import get_db
from app.main import app
from app.models.developer import Developer


HEADERS = {"X-Alduor-Extension-Token": "test-token"}


def mark_developer_merged(developer_id: int) -> None:
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        developer = db.get(Developer, developer_id)
        developer.record_status = "merged"
        db.commit()
    finally:
        db.close()


def test_entity_search_developers_and_projects(client, developer, project):
    response = client.get("/api/entities/search?q=Example&entity_type=all&limit=10", headers=HEADERS)
    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["entity_type"] for item in items} == {"developer", "project"}
    assert all(item["record_status"] == "active" for item in items)


def test_entity_search_excludes_merged_by_default(client, developer):
    mark_developer_merged(developer["id"])
    response = client.get("/api/entities/search?q=Example&entity_type=developer", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["items"] == []
