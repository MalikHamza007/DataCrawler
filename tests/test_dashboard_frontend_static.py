from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_static_assets_and_no_frontend_frameworks():
    required = [
        ROOT / "app/static/js/dashboard.js",
        ROOT / "app/static/js/state.js",
        ROOT / "app/static/js/dashboard-api.js",
        ROOT / "app/static/js/dashboard-map.js",
        ROOT / "app/static/css/dashboard.css",
        ROOT / "app/static/vendor/markerclusterer/markerclusterer.min.js",
        ROOT / "app/static/vendor/markerclusterer/LICENSE",
    ]
    for path in required:
        assert path.exists(), path
    all_text = "\n".join(path.read_text() for path in required if path.suffix in {".js", ".css"})
    assert "React" not in all_text
    assert "Vue" not in all_text
    assert "AbortController" in all_text
    assert "AdvancedMarkerElement" in all_text
    assert "innerHTML" not in all_text


def test_dashboard_handles_worker_contract_and_intentional_map_cancellation():
    dashboard = (ROOT / "app/static/js/dashboard.js").read_text()
    dashboard_api = (ROOT / "app/static/js/dashboard-api.js").read_text()
    dashboard_map = (ROOT / "app/static/js/dashboard-map.js").read_text()

    assert 'worker.status === "online"' in dashboard
    assert "worker.worker_online" not in dashboard
    assert "dashboardState.activeRequests[key] === controller" in dashboard_api
    assert "if (dashboardState.map) return;" in dashboard_map
    assert 'error.name === "AbortError"' in dashboard_map


def test_dashboard_exposes_real_area_collection_workflow():
    template = (ROOT / "app/templates/index.html").read_text()
    dashboard = (ROOT / "app/static/js/dashboard.js").read_text()
    dashboard_api = (ROOT / "app/static/js/dashboard-api.js").read_text()
    dashboard_map = (ROOT / "app/static/js/dashboard-map.js").read_text()

    for element_id in (
        "use-visible-area",
        "collection-area-input",
        "collection-area-options",
        "collection-radius-km",
        "draw-search-circle",
        "draw-search-rectangle",
        "draw-search-polygon",
        "finish-search-polygon",
        "collection-project-types",
        "start-area-search",
        "collection-job-status",
        "collection-research-metrics",
    ):
        assert f'id="{element_id}"' in template
    assert 'job_type: "places_discovery"' in dashboard
    assert "selectNamedCollectionArea" in dashboard
    assert "startCircleSelection" in dashboard
    assert "radius_meters" in dashboard
    assert "Submitting the search to the collector" in dashboard
    assert "Search could not start:" in dashboard
    assert "pollCollectionJob(job.id)" in dashboard
    assert 'request("collection-job-create", "/api/collection-jobs"' in dashboard_api
    assert 'request("lahore-zones", "/api/lahore-zones"' in dashboard_api
    assert "useNamedArea" in dashboard_map
    assert "new google.maps.Circle" in dashboard_map
    assert "new google.maps.Rectangle" in dashboard_map
    assert "new google.maps.Polygon" in dashboard_map


def test_dashboard_template_has_accessibility_and_map_id_warning():
    template = (ROOT / "app/templates/index.html").read_text()
    assert "aria-live" in template
    assert "aria-label" in template
    assert "GOOGLE_MAPS_MAP_ID" not in template
    assert "markerclusterer.min.js" in template
    assert "libraries=maps,marker" in template
