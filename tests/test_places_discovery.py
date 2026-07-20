from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.collectors.google_places.client import GooglePlacesClient
from app.core.config import Settings
from app.db.session import get_db
from app.main import app
from app.models.collection_job import CollectionJob
from app.models.contact import Contact
from app.models.project import Project
from app.models.project_discovery import ProjectDiscovery
from app.models.source_evidence import SourceEvidence
from app.services.places_discovery import discover_places_for_job, preview_places_plan
from app.services.website_enrichment import queue_for_places_job


def fixture(name: str) -> dict:
    path = Path(__file__).parent / "fixtures" / "google_places" / name
    return json.loads(path.read_text())


def places_settings(**overrides: object) -> Settings:
    values = {
        "google_places_enabled": True,
        "google_places_server_api_key": "test-fake-key",
        "google_places_request_delay_ms": 0,
        "google_places_max_retries": 2,
        "google_places_max_pages_per_query": 2,
        "google_places_max_queries_per_job": 2,
        "google_places_max_results_per_job": 10,
        "google_places_enable_nearby_search": False,
    }
    values.update(overrides)
    return Settings(**values)


def create_zone_job(client: TestClient, project_types: list[str] | None = None) -> dict:
    response = client.post(
        "/api/collection-jobs",
        json={
            "job_type": "places_discovery",
            "city": "Lahore",
            "lahore_zone": "Gulberg",
            "search_config_json": {
                "search_mode": "zone",
                "zone_id": "gulberg",
                "radius_meters": 5000,
                "project_types": project_types or ["apartments"],
                "map_center": {"lat": 31.5106, "lng": 74.3441},
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def db_session_from_app() -> object:
    override = app.dependency_overrides[get_db]
    generator = override()
    return next(generator), generator


def test_search_plan_and_dry_run_create_no_projects(client: TestClient) -> None:
    job = create_zone_job(client, ["apartments", "commercial"])
    db, generator = db_session_from_app()
    try:
        plan = preview_places_plan(db, job["id"], places_settings(google_places_dry_run=True))
        assert plan.query_count == 2
        assert plan.cell_count >= 1
        assert plan.estimated_max_requests == 4

        result = discover_places_for_job(db, job["id"], client=None, settings=places_settings(google_places_dry_run=True))
        assert result.dry_run is True
        assert result.requests_made == 0
        assert db.scalars(select(Project)).all() == []
    finally:
        db.close()
        generator.close()


def test_discovery_paginates_deduplicates_and_persists_projects(client: TestClient) -> None:
    job = create_zone_job(client)
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        if body.get("pageToken") == "NEXT_TOKEN":
            return httpx.Response(200, json=fixture("text_search_page_2.json"))
        return httpx.Response(200, json=fixture("text_search_page_1.json"))

    db, generator = db_session_from_app()
    try:
        google_client = GooglePlacesClient(settings=places_settings(), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        result = discover_places_for_job(db, job["id"], client=google_client, settings=places_settings())
        assert result.status == "completed"
        assert result.requests_made == 4
        assert result.raw_results == 8
        assert result.unique_place_ids == 3
        assert result.projects_created == 3
        assert result.contacts_created == 1
        assert result.websites_discovered == 1
        assert result.duplicates_skipped == 5
        assert calls[1]["pageToken"] == "NEXT_TOKEN"
        assert calls[0]["textQuery"] == calls[1]["textQuery"]
        assert calls[0]["locationRestriction"] == calls[1]["locationRestriction"]

        projects = db.scalars(select(Project).order_by(Project.google_place_id)).all()
        assert len(projects) == 3
        assert all(project.developer_id is None for project in projects)
        assert all(project.city == "Lahore" for project in projects)
        assert all(project.verification_status == "unverified" for project in projects)
        assert projects[0].official_website_url == "https://gulberg-heights.example.com/"
        assert len(db.scalars(select(Contact)).all()) == 1
        assert db.scalars(select(SourceEvidence)).all()
        assert len(db.scalars(select(ProjectDiscovery)).all()) == 8

        child_ids = queue_for_places_job(db, job["id"], places_settings(area_research_max_pages_per_website=4))
        assert len(child_ids) == 1
        child = db.get(CollectionJob, child_ids[0])
        assert child.job_type == "website_enrichment"
        assert child.status == "queued"
        assert child.search_config_json["parent_collection_job_id"] == job["id"]
        assert child.search_config_json["max_pages"] == 4

        summary_response = client.get(f"/api/collection-jobs/{job['id']}/research-summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["status"] == "running"
        assert summary["places"]["api_requests"] == 4
        assert summary["places"]["raw_results"] == 8
        assert summary["places"]["official_websites_found"] == 1
        assert summary["websites"]["queued"] == 1
        assert summary["websites"]["pending"] == 1
    finally:
        db.close()
        generator.close()


def test_existing_place_id_updates_only_blank_safe_fields(client: TestClient) -> None:
    job = create_zone_job(client)
    existing = client.post("/api/projects", json={"name": "Manual Name", "google_place_id": "place_demo_1"}).json()

    db, generator = db_session_from_app()
    try:
        google_client = GooglePlacesClient(
            settings=places_settings(google_places_max_pages_per_query=1),
            http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=fixture("text_search_page_1.json")))),
        )
        result = discover_places_for_job(db, job["id"], client=google_client, settings=places_settings(google_places_max_pages_per_query=1))
        assert result.projects_created == 1
        assert result.projects_updated == 1
        project = db.get(Project, existing["id"])
        assert project.name == "Manual Name"
        assert project.address == "Gulberg, Lahore"
    finally:
        db.close()
        generator.close()


def test_polygon_discards_outside_results_and_job_failure(client: TestClient) -> None:
    response = client.post(
        "/api/collection-jobs",
        json={
            "job_type": "places_discovery",
            "city": "Lahore",
            "search_config_json": {
                "search_mode": "polygon",
                "project_types": ["apartments"],
                "geometry": {
                    "type": "polygon",
                    "coordinates": [
                        {"lat": 31.50, "lng": 74.33},
                        {"lat": 31.53, "lng": 74.33},
                        {"lat": 31.50, "lng": 74.36}
                    ]
                }
            },
        },
    )
    assert response.status_code == 201
    db, generator = db_session_from_app()
    try:
        google_client = GooglePlacesClient(
            settings=places_settings(google_places_max_pages_per_query=1),
            http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=fixture("text_search_page_1.json")))),
        )
        result = discover_places_for_job(db, response.json()["id"], client=google_client, settings=places_settings(google_places_max_pages_per_query=1))
        assert result.results_outside_geometry >= 1
    finally:
        db.close()
        generator.close()


def test_normal_job_creation_makes_no_google_request(client: TestClient) -> None:
    called = {"value": False}

    def handler(_: httpx.Request) -> httpx.Response:
        called["value"] = True
        return httpx.Response(200, json={})

    _ = httpx.Client(transport=httpx.MockTransport(handler))
    job = create_zone_job(client)
    assert job["status"] == "queued"
    assert called["value"] is False
