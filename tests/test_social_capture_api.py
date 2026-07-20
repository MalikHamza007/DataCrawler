from __future__ import annotations

from datetime import UTC, datetime

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


def payload(**overrides):
    base = {
        "capture": {
            "capture_version": "1",
            "platform": "facebook",
            "page_kind": "business_profile",
            "source_url": "https://www.facebook.com/exampledevelopers",
            "canonical_url": "https://www.facebook.com/exampledevelopers",
            "page_title": "Example Developers",
            "profile_name": "Example Developers",
            "username": "exampledevelopers",
            "visible_text_excerpt": "Example Developers sales office 0300 1234567 Pearl Heights Lahore",
            "about_text": "Public real estate developer in Lahore.",
            "project_names": ["Pearl Heights"],
            "phones": [{"value": "0300 1234567", "label": "Sales"}],
            "emails": [{"value": "sales@example.com", "label": "Business"}],
            "whatsapp": [{"value": "923001234567", "url": "https://wa.me/923001234567"}],
            "addresses": ["Main Boulevard Gulberg Lahore"],
            "websites": ["https://example.com"],
            "external_links": [],
            "campaign": None,
            "captured_at": datetime(2026, 7, 13, tzinfo=UTC).isoformat(),
            "extractor_version": "facebook-v1",
            "warnings": [],
        },
        "selected_fields": [
            {"field_name": "phone", "source_label": "Sales", "original_extracted_value": "0300 1234567", "submitted_value": "0300 1234567", "include": True, "target_entity": "developer"},
            {"field_name": "official_website", "source_label": "Website", "original_extracted_value": "https://example.com", "submitted_value": "https://example.com", "include": True, "target_entity": "developer"},
            {"field_name": "address", "source_label": "Address", "original_extracted_value": "Main Boulevard Gulberg Lahore", "submitted_value": "Main Boulevard Gulberg Lahore", "include": False, "target_entity": "developer"},
        ],
        "extension_version": "0.1.0",
        "operator_note": "reviewed visible fields",
    }
    base.update(overrides)
    return base


def test_create_attached_developer_capture_creates_children(client, developer):
    response = client.post("/api/social-captures", json=payload(developer_id=developer["id"]), headers=HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "attached"
    assert data["source_evidence_created"] >= 2
    assert data["contacts_created"] == 1
    assert data["social_profiles_created"] == 1


def test_create_unassigned_capture_enters_inbox(client):
    body = payload()
    body["capture"]["source_url"] = "https://example.com/public"
    body["capture"]["canonical_url"] = "https://example.com/public"
    response = client.post("/api/social-captures", json=body, headers=HEADERS)
    assert response.status_code == 201
    assert response.json()["status"] == "unassigned"
    inbox = client.get("/api/social-captures?review_status=unassigned")
    assert inbox.status_code == 200
    assert len(inbox.json()) == 1


def test_duplicate_capture_returns_conflict(client, developer):
    body = payload(developer_id=developer["id"])
    first = client.post("/api/social-captures", json=body, headers=HEADERS)
    second = client.post("/api/social-captures", json=body, headers=HEADERS)
    assert first.status_code == 201
    assert second.status_code == 409
    assert "Duplicate capture already exists" in second.json()["detail"]


def test_merged_target_rejected(client, developer):
    mark_developer_merged(developer["id"])
    response = client.post("/api/social-captures", json=payload(developer_id=developer["id"]), headers=HEADERS)
    assert response.status_code == 422
