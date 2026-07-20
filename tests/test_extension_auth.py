from __future__ import annotations


def test_extension_status_requires_token(client):
    assert client.get("/api/extension/status").status_code == 403
    assert client.get("/api/extension/status", headers={"X-Alduor-Extension-Token": "bad"}).status_code == 403
    response = client.get("/api/extension/status", headers={"X-Alduor-Extension-Token": "test-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert "token" not in data

