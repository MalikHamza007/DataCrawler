from __future__ import annotations

from collections.abc import Generator
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

os.environ["GOOGLE_MAPS_BROWSER_API_KEY"] = ""
os.environ["GOOGLE_MAPS_MAP_ID"] = ""
os.environ["GOOGLE_PLACES_SERVER_API_KEY"] = ""
os.environ["GOOGLE_PLACES_ENABLED"] = "false"
os.environ["ALDUOR_EXTENSION_API_TOKEN"] = "test-token"
os.environ["ALDUOR_EXTENSION_ENABLED"] = "true"

from app.db.base import Base
from app.db.session import get_db, make_engine
from app.main import app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = make_engine(database_url)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def developer(client: TestClient) -> dict:
    response = client.post("/api/developers", json={"name": "Example Developers"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture()
def project(client: TestClient) -> dict:
    response = client.post("/api/projects", json={"name": "Example Heights", "lahore_zone": "Gulberg"})
    assert response.status_code == 201
    return response.json()
