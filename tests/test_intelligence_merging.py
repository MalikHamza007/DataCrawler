from sqlalchemy import select

from app.intelligence.merging import execute_merge, merge_preview
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.intelligence import DuplicateCandidate, MergeOperation
from app.models.project import Project
from app.models.source_evidence import SourceEvidence


def db_from_client(client):
    dependency = next(iter(client.app.dependency_overrides.values())); return next(dependency())


def test_developer_preview_is_read_only_and_merge_preserves_children(client):
    db = db_from_client(client)
    try:
        survivor = Developer(name="Alpha Developers", normalized_name="alpha developers", website_url=None, city="Lahore", country="Pakistan")
        absorbed = Developer(name="Alpha Developers Ltd", normalized_name="alpha developers ltd", website_url="https://alpha.com", city="Lahore", country="Pakistan")
        db.add_all([survivor, absorbed]); db.flush()
        project = Project(name="Alpha Heights", normalized_name="alpha heights", developer_id=absorbed.id, city="Lahore", country="Pakistan")
        db.add(project); db.add_all([Contact(developer_id=survivor.id, contact_type="phone", value="0300", normalized_value="0300"), Contact(developer_id=absorbed.id, contact_type="phone", value="0300", normalized_value="0300"), Contact(developer_id=absorbed.id, contact_type="email", value="sales@alpha.com", normalized_value="sales@alpha.com")]); db.flush()
        evidence = SourceEvidence(developer_id=absorbed.id, source_type="official_website", source_url="https://alpha.com", field_name="developer_name", extracted_value="Alpha Developers", verification_status="unverified")
        db.add(evidence); db.flush(); candidate = DuplicateCandidate(entity_type="developer", left_developer_id=min(survivor.id, absorbed.id), right_developer_id=max(survivor.id, absorbed.id), duplicate_score=95, confidence_level="high", signals_json=[], explanation="same", rule_version="m6-v1", status="confirmed_duplicate")
        db.add(candidate); db.commit()
        preview = merge_preview(db, candidate.id, survivor.id)
        assert preview["field_actions"]["website_url"]["action"] == "fill_survivor" and preview["contacts"] == {"move": 1, "exact_duplicates": 1}
        assert absorbed.record_status == "active" and not db.scalars(select(MergeOperation)).all()
        operation = execute_merge(db, candidate.id, survivor.id, "Confirmed duplicate")
        assert operation.status == "completed" and survivor.website_url == "https://alpha.com"
        assert absorbed.record_status == "merged" and absorbed.merged_into_developer_id == survivor.id
        assert project.developer_id == survivor.id and evidence.developer_id == survivor.id
        assert len(db.scalars(select(Contact).where(Contact.developer_id == survivor.id)).all()) == 2
        assert candidate.status == "merged"
    finally: db.close()


def test_project_merge_soft_merges_and_conflicting_developers_block(client):
    db = db_from_client(client)
    try:
        dev1 = Developer(name="One", normalized_name="one", city="Lahore", country="Pakistan"); dev2 = Developer(name="Two", normalized_name="two", city="Lahore", country="Pakistan")
        db.add_all([dev1, dev2]); db.flush()
        left = Project(name="Alpha", normalized_name="alpha", developer_id=dev1.id, city="Lahore", country="Pakistan")
        right = Project(name="Alpha Heights", normalized_name="alpha heights", developer_id=dev2.id, city="Lahore", country="Pakistan")
        db.add_all([left, right]); db.flush(); candidate = DuplicateCandidate(entity_type="project", left_project_id=left.id, right_project_id=right.id, duplicate_score=80, confidence_level="high", signals_json=[], explanation="similar", rule_version="m6-v1", status="confirmed_duplicate")
        db.add(candidate); db.commit()
        import pytest
        from app.core.exceptions import ConflictError
        with pytest.raises(ConflictError): execute_merge(db, candidate.id, left.id)
        assert left.record_status == right.record_status == "active" and candidate.status == "confirmed_duplicate"
        right.developer_id = dev1.id; db.commit(); operation = execute_merge(db, candidate.id, left.id)
        assert operation.status == "completed" and right.record_status == "merged" and right.merged_into_project_id == left.id
    finally: db.close()
