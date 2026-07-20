from sqlalchemy import select

from app.intelligence.classification import assess_developer, assess_project, review_assessment
from app.models.developer import Developer
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.source_evidence import SourceEvidence


def db_from_client(client):
    dependency = next(iter(client.app.dependency_overrides.values())); return next(dependency())


def evidence(db, *, developer_id=None, project_id=None, text="", field="description"):
    item = SourceEvidence(developer_id=developer_id, project_id=project_id, source_type="official_website", source_url="https://example.com/source", captured_text=text, field_name=field, extracted_value=text, verification_status="unverified")
    db.add(item); db.commit(); db.refresh(item); return item


def test_developer_rules_and_manual_decision_survive_recalculation(client):
    db = db_from_client(client)
    try:
        developer = Developer(name="Alpha Developers", normalized_name="alpha developers", classification="uncertain", verification_status="unverified", city="Lahore", country="Pakistan")
        db.add(developer); db.commit(); db.refresh(developer)
        source = evidence(db, developer_id=developer.id, text="We are a property developer. Our developments include Alpha Heights.", field="project_name")
        project1 = Project(name="Alpha Heights", normalized_name="alpha heights", city="Lahore", country="Pakistan")
        project2 = Project(name="Alpha Square", normalized_name="alpha square", city="Lahore", country="Pakistan")
        db.add_all([project1, project2]); db.flush()
        db.add_all([ProjectDeveloperRelationship(project_id=project1.id, developer_id=developer.id, relationship_type="developer", status="candidate", source_evidence_id=source.id, source_url=source.source_url, evidence_text="Alpha Heights is developed by Alpha Developers"), ProjectDeveloperRelationship(project_id=project2.id, developer_id=developer.id, relationship_type="developer", status="candidate", source_url="https://example.com/two", evidence_text="A project by Alpha Developers")]); db.commit()
        assessment = assess_developer(db, developer.id)
        assert assessment.system_score >= 60 and assessment.suggested_classification in {"probable_developer", "verified_developer"}
        assert all("source_evidence_ids" in item for item in assessment.signals_json)
        review_assessment(db, assessment.id, "override", "developer_marketing_hybrid", "Manual evidence review")
        recalculated = assess_developer(db, developer.id)
        assert recalculated.assessment_status == "overridden" and recalculated.manual_classification == "developer_marketing_hybrid"
        assert db.get(Developer, developer.id).verification_status == "unverified"
    finally: db.close()


def test_broker_construction_and_insufficient_evidence(client):
    db = db_from_client(client)
    try:
        broker = Developer(name="Dealer Co", normalized_name="dealer co", city="Lahore", country="Pakistan")
        builder = Developer(name="Builder Co", normalized_name="builder co", city="Lahore", country="Pakistan")
        empty = Developer(name="Unknown Co", normalized_name="unknown co", city="Lahore", country="Pakistan")
        db.add_all([broker, builder, empty]); db.commit()
        evidence(db, developer_id=broker.id, text="Authorized dealer and property consultant")
        evidence(db, developer_id=builder.id, text="General contractor and construction services")
        assert assess_developer(db, broker.id).suggested_classification == "broker_agency"
        assert assess_developer(db, builder.id).suggested_classification == "construction_company"
        assessment = assess_developer(db, empty.id)
        assert assessment.confidence_level == "insufficient_evidence" and assessment.signals_json == []
    finally: db.close()


def test_project_classification_uses_official_evidence_without_verifying(client):
    db = db_from_client(client)
    try:
        project = Project(name="Alpha Heights", normalized_name="alpha heights", project_type="apartments", project_status="booking_open", city="Lahore", country="Pakistan", official_website_url="https://example.com/projects/alpha")
        db.add(project); db.commit(); evidence(db, project_id=project.id, text="Alpha Heights apartments in Lahore booking open", field="project_name")
        assessment = assess_project(db, project.id)
        assert assessment.system_score >= 60 and assessment.suggested_classification in {"probable_project", "verified_project"}
        assert project.verification_status == "unverified"
    finally: db.close()
