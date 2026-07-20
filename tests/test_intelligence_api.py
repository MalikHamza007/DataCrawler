from sqlalchemy import select

from app.models.developer import Developer
from app.models.intelligence import DuplicateCandidate
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.source_evidence import SourceEvidence


def db_from_client(client):
    dependency = next(iter(client.app.dependency_overrides.values())); return next(dependency())


def test_classification_and_relationship_review_endpoints(client):
    developer = client.post("/api/developers", json={"name": "Alpha Developers"}).json()
    project = client.post("/api/projects", json={"name": "Alpha Heights"}).json()
    db = db_from_client(client)
    try:
        db.add(SourceEvidence(developer_id=developer["id"], source_type="official_website", source_url="https://alpha.com", captured_text="We are a property developer", field_name="description", extracted_value="property developer", verification_status="unverified"))
        relationship = ProjectDeveloperRelationship(project_id=project["id"], developer_id=developer["id"], relationship_type="developer", status="candidate", source_url="https://alpha.com/heights", evidence_text="Alpha Heights is developed by Alpha Developers")
        db.add(relationship); db.commit(); relationship_id = relationship.id
    finally: db.close()
    assessment = client.post(f"/api/developers/{developer['id']}/classification/recalculate").json()
    assert assessment["signals_json"] and assessment["rule_version"] == "m6-v1"
    confirmed = client.post(f"/api/classification-assessments/{assessment['id']}/confirm", json={"review_note": "Reviewed"})
    assert confirmed.status_code == 200 and confirmed.json()["assessment_status"] == "confirmed"
    scored = client.post(f"/api/project-developer-relationships/{relationship_id}/recalculate")
    assert scored.status_code == 200 and scored.json()["status"] == "candidate"
    verified = client.post(f"/api/project-developer-relationships/{relationship_id}/verify", json={"review_note": "Official evidence"})
    assert verified.status_code == 200 and verified.json()["status"] == "verified"
    assert client.get("/api/classification-assessments?limit=101").status_code == 422


def test_duplicate_scan_review_preview_and_merge_api(client):
    left = client.post("/api/developers", json={"name": "ABS Developers", "website_url": "https://abs.com"}).json()
    right = client.post("/api/developers", json={"name": "ABS Developers Pvt Ltd", "website_url": "https://www.abs.com"}).json()
    job = client.post("/api/duplicate-scans", json={"entity_type": "developer", "minimum_score": 55})
    assert job.status_code == 201 and job.json()["status"] == "queued"
    db = db_from_client(client)
    try:
        candidate = DuplicateCandidate(entity_type="developer", left_developer_id=min(left["id"], right["id"]), right_developer_id=max(left["id"], right["id"]), duplicate_score=90, confidence_level="high", signals_json=[], explanation="same domain", rule_version="m6-v1", status="pending")
        db.add(candidate); db.commit(); candidate_id = candidate.id
    finally: db.close()
    assert client.post(f"/api/duplicate-candidates/{candidate_id}/confirm", json={"review_note": "Reviewed"}).json()["status"] == "confirmed_duplicate"
    preview = client.post(f"/api/duplicate-candidates/{candidate_id}/merge-preview", json={"survivor_id": left["id"]})
    assert preview.status_code == 200 and preview.json()["absorbed_id"] == right["id"]
    merged = client.post(f"/api/duplicate-candidates/{candidate_id}/merge", json={"survivor_id": left["id"], "operator_note": "Same company"})
    assert merged.status_code == 200 and merged.json()["status"] == "completed"
    absorbed = client.get(f"/api/developers/{right['id']}").json()
    assert absorbed["record_status"] == "merged" and absorbed["merged_into_developer_id"] == left["id"]
    assert all(item["id"] != right["id"] for item in client.get("/api/developers").json())
