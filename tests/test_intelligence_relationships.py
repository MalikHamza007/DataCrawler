import pytest

from app.core.exceptions import ConflictError
from app.intelligence.relationships import reject_relationship, score_relationship, verify_relationship
from app.models.developer import Developer
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship


def db_from_client(client):
    dependency = next(iter(client.app.dependency_overrides.values())); return next(dependency())


def test_relationship_scoring_verification_and_rejection(client):
    db = db_from_client(client)
    try:
        developer = Developer(name="Alpha", normalized_name="alpha", website_url="https://alpha.com", city="Lahore", country="Pakistan")
        project = Project(name="Alpha Heights", normalized_name="alpha heights", official_website_url="https://alpha.com/heights", city="Lahore", country="Pakistan")
        other = Project(name="Alpha Square", normalized_name="alpha square", city="Lahore", country="Pakistan")
        db.add_all([developer, project, other]); db.flush()
        relationship = ProjectDeveloperRelationship(project_id=project.id, developer_id=developer.id, relationship_type="developer", status="candidate", source_url="https://alpha.com/heights", evidence_text="Alpha Heights is developed by Alpha")
        rejected = ProjectDeveloperRelationship(project_id=other.id, developer_id=developer.id, relationship_type="developer", status="candidate", source_url="https://alpha.com/square", evidence_text="Marketing by Alpha")
        db.add_all([relationship, rejected]); db.commit()
        scored = score_relationship(db, relationship.id)
        assert scored.system_score == 90 and {s["code"] for s in scored.signals_json} == {"EXPLICIT_DEVELOPED_BY", "MATCHING_DOMAIN"}
        verified = verify_relationship(db, relationship.id, "Confirmed official evidence")
        assert verified.status == "verified" and project.developer_id == developer.id
        rejected = reject_relationship(db, rejected.id, "Marketing only")
        score_relationship(db, rejected.id)
        assert rejected.status == "rejected"
    finally: db.close()


def test_relationship_verify_conflict(client):
    db = db_from_client(client)
    try:
        left = Developer(name="Left", normalized_name="left", city="Lahore", country="Pakistan")
        right = Developer(name="Right", normalized_name="right", city="Lahore", country="Pakistan")
        db.add_all([left, right]); db.flush()
        project = Project(name="Project", normalized_name="project", developer_id=left.id, city="Lahore", country="Pakistan")
        db.add(project); db.flush(); relationship = ProjectDeveloperRelationship(project_id=project.id, developer_id=right.id, relationship_type="developer", status="candidate", source_url="https://right.com/project", evidence_text="Developed by Right")
        db.add(relationship); db.commit()
        with pytest.raises(ConflictError): verify_relationship(db, relationship.id, "conflict")
        assert relationship.status == "candidate" and project.developer_id == left.id
    finally: db.close()
