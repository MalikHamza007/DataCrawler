from fastapi.testclient import TestClient


def test_social_profiles(client: TestClient, developer: dict, project: dict) -> None:
    facebook = client.post(
        "/api/social-profiles",
        json={"developer_id": developer["id"], "platform": "facebook", "profile_url": "https://Facebook.com/ExampleDev/"},
    )
    assert facebook.status_code == 201
    assert facebook.json()["normalized_url"] == "https://facebook.com/ExampleDev"

    instagram = client.post(
        "/api/social-profiles",
        json={"project_id": project["id"], "platform": "instagram", "profile_url": "https://instagram.com/exampleheights/"},
    )
    assert instagram.status_code == 201

    update = client.patch(f"/api/social-profiles/{instagram.json()['id']}", json={"is_official": True})
    assert update.status_code == 200
    assert update.json()["is_official"] is True

    filtered = client.get("/api/social-profiles", params={"platform": "instagram"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1


def test_invalid_social_profile(client: TestClient, developer: dict, project: dict) -> None:
    two_owners = client.post(
        "/api/social-profiles",
        json={
            "developer_id": developer["id"],
            "project_id": project["id"],
            "platform": "facebook",
            "profile_url": "https://facebook.com/example",
        },
    )
    assert two_owners.status_code == 422

    bad_platform = client.post(
        "/api/social-profiles",
        json={"developer_id": developer["id"], "platform": "myspace", "profile_url": "https://example.com"},
    )
    assert bad_platform.status_code == 422
