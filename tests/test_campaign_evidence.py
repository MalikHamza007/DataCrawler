from __future__ import annotations

from copy import deepcopy

from tests.test_social_capture_api import HEADERS, payload


def test_meta_ad_library_capture_creates_verified_campaign(client, project):
    body = payload(project_id=project["id"])
    body["capture"]["platform"] = "meta_ad_library"
    body["capture"]["page_kind"] = "ad_library_result"
    body["capture"]["source_url"] = "https://www.facebook.com/ads/library/?id=1"
    body["capture"]["canonical_url"] = "https://www.facebook.com/ads/library/?id=1"
    body["capture"]["extractor_version"] = "meta-ad-library-v1"
    body["capture"]["campaign"] = {
        "campaign_type": "meta_ad_library",
        "advertiser_name": "Example Developers",
        "campaign_text": "Book your apartment.",
        "call_to_action": "Learn More",
        "destination_url": "https://example.com/project",
        "visible_status": "active_visible",
        "verification_status": "captured_from_ad_library",
    }
    response = client.post("/api/social-captures", json=body, headers=HEADERS)
    assert response.status_code == 201
    assert response.json()["campaign_evidence_created"] == 1
    evidence = client.get(f"/api/social-captures/{response.json()['id']}/campaign-evidence").json()
    assert evidence[0]["verification_status"] == "captured_from_ad_library"


def test_normal_facebook_post_not_confirmed_paid_ad(client, project):
    body = deepcopy(payload(project_id=project["id"]))
    body["capture"]["page_kind"] = "promotional_post"
    body["capture"]["source_url"] = "https://www.facebook.com/example/posts/1"
    body["capture"]["canonical_url"] = "https://www.facebook.com/example/posts/1"
    body["capture"]["campaign"] = {
        "campaign_type": "public_promotional_post",
        "advertiser_name": "Example Developers",
        "campaign_text": "Book your apartment.",
        "call_to_action": "Learn More",
        "destination_url": "https://example.com/project",
        "visible_status": "status_not_visible",
        "verification_status": "captured_from_ad_library",
    }
    response = client.post("/api/social-captures", json=body, headers=HEADERS)
    assert response.status_code == 201
    evidence = client.get(f"/api/social-captures/{response.json()['id']}/campaign-evidence").json()
    assert evidence[0]["verification_status"] == "public_post_only"
