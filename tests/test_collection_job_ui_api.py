from fastapi.testclient import TestClient


def base_types() -> list[str]:
    return ["apartments", "commercial", "mixed_use"]


def create_job(client: TestClient, config: dict) -> object:
    return client.post(
        "/api/collection-jobs",
        json={
            "job_type": "places_discovery",
            "city": "Lahore",
            "lahore_zone": "Gulberg" if config["search_mode"] == "zone" else None,
            "search_config_json": config,
        },
    )


def test_create_zone_based_collection_job(client: TestClient) -> None:
    response = create_job(
        client,
        {
            "search_mode": "zone",
            "zone_id": "gulberg",
            "radius_meters": 5000,
            "project_types": base_types(),
            "map_center": {"lat": 31.5106, "lng": 74.3441},
        },
    )
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "queued"
    assert job["search_config_json"]["zone_id"] == "gulberg"


def test_create_radius_based_collection_job(client: TestClient) -> None:
    response = create_job(
        client,
        {
            "search_mode": "radius",
            "radius_meters": 4000,
            "project_types": base_types(),
            "map_center": {"lat": 31.5204, "lng": 74.3587},
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_create_rectangle_based_collection_job(client: TestClient) -> None:
    response = create_job(
        client,
        {
            "search_mode": "rectangle",
            "project_types": base_types(),
            "geometry": {"type": "rectangle", "north": 31.54, "south": 31.49, "east": 74.38, "west": 74.32},
        },
    )
    assert response.status_code == 201
    assert response.json()["search_config_json"]["geometry"]["type"] == "rectangle"


def test_create_polygon_based_collection_job(client: TestClient) -> None:
    response = create_job(
        client,
        {
            "search_mode": "polygon",
            "project_types": ["apartments", "residential_tower"],
            "geometry": {
                "type": "polygon",
                "coordinates": [
                    {"lat": 31.52, "lng": 74.33},
                    {"lat": 31.54, "lng": 74.36},
                    {"lat": 31.50, "lng": 74.39},
                ],
            },
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_reject_invalid_zone_radius_project_types_and_polygon(client: TestClient) -> None:
    invalid_zone = create_job(client, {"search_mode": "zone", "zone_id": "unknown", "radius_meters": 5000, "project_types": base_types()})
    assert invalid_zone.status_code == 422

    invalid_radius = create_job(
        client,
        {"search_mode": "radius", "radius_meters": 9999, "project_types": base_types(), "map_center": {"lat": 31.52, "lng": 74.35}},
    )
    assert invalid_radius.status_code == 422

    empty_types = create_job(client, {"search_mode": "zone", "zone_id": "gulberg", "radius_meters": 5000, "project_types": []})
    assert empty_types.status_code == 422

    unknown_type = create_job(client, {"search_mode": "zone", "zone_id": "gulberg", "radius_meters": 5000, "project_types": ["castle"]})
    assert unknown_type.status_code == 422

    invalid_polygon = create_job(
        client,
        {
            "search_mode": "polygon",
            "project_types": base_types(),
            "geometry": {"type": "polygon", "coordinates": [{"lat": 31.52, "lng": 74.33}, {"lat": 31.54, "lng": 74.36}]},
        },
    )
    assert invalid_polygon.status_code == 422


def test_reject_geometry_outside_lahore_and_no_places_call(client: TestClient) -> None:
    response = create_job(
        client,
        {
            "search_mode": "rectangle",
            "project_types": base_types(),
            "geometry": {"type": "rectangle", "north": 32.0, "south": 31.9, "east": 74.38, "west": 74.32},
        },
    )
    assert response.status_code == 422

    jobs = client.get("/api/collection-jobs", params={"job_type": "places_discovery"})
    assert jobs.status_code == 200
    assert jobs.json() == []


def test_collection_job_lahore_zone_filter(client: TestClient) -> None:
    create_job(
        client,
        {
            "search_mode": "zone",
            "zone_id": "gulberg",
            "radius_meters": 5000,
            "project_types": base_types(),
            "map_center": {"lat": 31.5106, "lng": 74.3441},
        },
    )
    response = client.get("/api/collection-jobs", params={"lahore_zone": "Gulberg"})
    assert response.status_code == 200
    assert len(response.json()) == 1
