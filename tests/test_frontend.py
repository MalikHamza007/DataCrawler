from pathlib import Path

from fastapi.testclient import TestClient


def test_dashboard_route_and_assets(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "Alduor Lahore Project Discovery Agent" in body
    assert "/static/css/app.css" in body
    assert "/static/js/api.js" in body
    assert "/static/js/map.js" in body
    assert "/static/js/jobs.js" in body
    assert "/static/js/app.js" in body
    assert "Google Maps is not configured" in body


def test_static_files_accessible(client: TestClient) -> None:
    assert client.get("/static/css/app.css").status_code == 200
    assert client.get("/static/js/api.js").status_code == 200
    assert client.get("/static/js/map.js").status_code == 200
    assert client.get("/static/js/jobs.js").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200


def test_no_frontend_build_tooling_introduced() -> None:
    backend = Path(__file__).resolve().parents[1]
    root = backend.parent
    assert not (root / "package.json").exists()
    assert not (root / "vite.config.js").exists()
    assert not (root / "webpack.config.js").exists()
    assert (backend / "app/static/css/app.css").exists()
    assert (backend / "app/static/js/app.js").exists()
