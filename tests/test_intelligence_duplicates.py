from sqlalchemy import select

from app.core.config import Settings
from app.intelligence.duplicates import generate_pairs, scan_duplicates, score_pair
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.intelligence import DuplicateCandidate
from app.models.project import Project


def db_from_client(client):
    dependency = next(iter(client.app.dependency_overrides.values())); return next(dependency())


def test_developer_blocking_scoring_and_review_preservation(client):
    db = db_from_client(client)
    try:
        left = Developer(name="ABS Developers Pvt Ltd", normalized_name="abs developers pvt ltd", website_url="https://abs.com", office_address="Plot 12 Gulberg III Boulevard", city="Lahore", country="Pakistan")
        right = Developer(name="ABS Developers Private Limited", normalized_name="abs developers private limited", website_url="https://www.abs.com", office_address="Plot 12, Gulberg 3 Blvd", city="Lahore", country="Pakistan")
        unrelated = Developer(name="Other Properties", normalized_name="other properties", city="Lahore", country="Pakistan")
        db.add_all([left, right, unrelated]); db.flush()
        db.add_all([Contact(developer_id=left.id, contact_type="phone", value="03001234567", normalized_value="+923001234567"), Contact(developer_id=right.id, contact_type="phone", value="+923001234567", normalized_value="+923001234567")]); db.commit()
        pairs, _ = generate_pairs(db, "developer")
        assert (left.id, right.id) in pairs and all(pair[0] < pair[1] for pair in pairs)
        score, signals = score_pair(db, "developer", left.id, right.id)
        assert score == 100 and {s["code"] for s in signals} >= {"EXACT_CONTACT", "SAME_DOMAIN"}
        summary = scan_duplicates(db, "developer")
        candidate = db.scalar(select(DuplicateCandidate))
        assert summary["candidates_created"] == 1 and candidate.status == "pending"
        candidate.status = "not_duplicate"; db.commit(); scan_duplicates(db, "developer")
        assert candidate.status == "not_duplicate"
    finally: db.close()


def test_project_scoring_distance_and_distinct_towers(client):
    db = db_from_client(client)
    try:
        one = Project(name="Alpha Tower A", normalized_name="alpha tower a", official_website_url="https://alpha.com/a", lahore_zone="Gulberg", latitude=31.5, longitude=74.3, city="Lahore", country="Pakistan")
        two = Project(name="Alpha Tower B", normalized_name="alpha tower b", official_website_url="https://alpha.com/b", lahore_zone="Gulberg", latitude=31.5001, longitude=74.3, city="Lahore", country="Pakistan")
        db.add_all([one, two]); db.commit()
        score, signals = score_pair(db, "project", one.id, two.id)
        assert "DISTINCT_PHASE" in {s["code"] for s in signals} and score < 80
        assert not db.scalars(select(DuplicateCandidate)).all()
    finally: db.close()


def test_pair_limit_is_enforced(client):
    db = db_from_client(client)
    try:
        for index in range(4): db.add(Developer(name=f"Same Group {index}", normalized_name=f"same group {index}", city="Lahore", country="Pakistan"))
        db.commit()
        settings = Settings(developer_duplicate_max_pair_comparisons=2)
        import pytest
        with pytest.raises(ValueError): generate_pairs(db, "developer", settings)
    finally: db.close()
