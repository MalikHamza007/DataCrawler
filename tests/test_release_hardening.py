from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.commands._ops import quick_check
from app.commands.verify_backup import verify


def test_security_headers_and_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "release-test-1"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "release-test-1"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_ready_and_system_status(client):
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    status = client.get("/api/system/status")
    assert status.status_code == 200
    data = status.json()
    assert data["version"] == "0.10.0"
    assert "google_places_server_api_key" not in json.dumps(data).lower()
    storage = client.get("/api/system/storage")
    assert storage.status_code == 200
    assert "database_size_bytes" in storage.json()


def test_sqlite_backup_manifest_verification(tmp_path):
    database = tmp_path / "source.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT)")
        connection.execute("INSERT INTO alembic_version VALUES ('test')")
    backup_dir = tmp_path / "alduor_backup_test"
    backup_dir.mkdir()
    backup_db = backup_dir / "database.sqlite3"
    backup_db.write_bytes(database.read_bytes())
    import hashlib

    digest = hashlib.sha256(backup_db.read_bytes()).hexdigest()
    (backup_dir / "manifest.json").write_text(json.dumps({"backup_version": "m10-v1", "database_filename": "database.sqlite3", "database_sha256": digest}), encoding="utf-8")
    assert quick_check(backup_db) == "ok"
    verify(backup_dir)


def test_release_files_exist():
    backend = Path(__file__).resolve().parents[1]
    assert (backend / "Dockerfile").exists()
    repo = backend.parent
    assert (repo / "compose.yaml").exists()
    assert (repo / ".dockerignore").exists()
    assert (repo / "VERSION").read_text(encoding="utf-8").strip() == "0.10.0"
    compose = (repo / "compose.yaml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8000:8000"' in compose
    assert "redis" not in compose.lower()
