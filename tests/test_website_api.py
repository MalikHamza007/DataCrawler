from app.core.config import Settings


def test_preview_is_isolated_and_canonical(client, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("preview must not perform DNS or HTTP")

    monkeypatch.setattr("socket.getaddrinfo", no_network)
    response = client.post("/api/website-enrichment/preview", json={"seed_url": "HTTPS://Example.COM/path#x", "crawl_mode": "unknown_official_site"})
    assert response.status_code == 200
    assert response.json()["canonical_seed_url"] == "https://example.com/path"
    assert response.json()["ssrf_check"] == "passed_syntax_only"


def test_project_developer_and_manual_jobs_queue_without_http(client, project, developer, monkeypatch):
    def no_http(*args, **kwargs):
        raise AssertionError("job creation must not make website requests")

    monkeypatch.setattr("app.collectors.websites.client.WebsiteClient.fetch", no_http)
    responses = [
        client.post(f"/api/projects/{project['id']}/website-enrichment-jobs", json={"seed_url": "https://project.example.com"}),
        client.post(f"/api/developers/{developer['id']}/website-enrichment-jobs", json={"seed_url": "https://developer.example.com"}),
        client.post("/api/website-enrichment-jobs", json={"seed_url": "https://manual.example.com", "crawl_mode": "unknown_official_site"}),
    ]
    assert [response.status_code for response in responses] == [201, 201, 201]
    assert all(response.json()["status"] == "queued" for response in responses)


def test_job_validation_and_crawl_details(client, project):
    assert client.post(f"/api/projects/{project['id']}/website-enrichment-jobs", json={}).status_code == 422
    assert client.post(f"/api/projects/{project['id']}/website-enrichment-jobs", json={"seed_url": "http://127.0.0.1"}).status_code == 400
    assert client.post("/api/projects/999/website-enrichment-jobs", json={"seed_url": "https://example.com"}).status_code == 404
    job = client.post(f"/api/projects/{project['id']}/website-enrichment-jobs", json={"seed_url": "https://example.com"}).json()
    crawls = client.get("/api/collection-jobs").json()
    assert job["job_type"] == "website_enrichment"
    # The crawl is created synchronously as queue metadata, not fetched content.
    from app.models.website_crawl import WebsiteCrawl
    from app.db.session import get_db
    assert job["total_items"] == 25


def test_configuration_limits():
    try:
        Settings(website_crawler_max_pages_per_site=0)
        assert False
    except ValueError:
        pass
    try:
        Settings(website_crawler_max_pages_per_site=5, website_crawler_playwright_max_pages=6)
        assert False
    except ValueError:
        pass
