from pathlib import Path

from app.collectors.websites.page_priority import score_link
from app.collectors.websites.parser import content_hash, parse_html, should_use_playwright

FIXTURES = Path(__file__).parent / "fixtures" / "websites"


def test_developer_page_extracts_identity_socials_and_links():
    page = parse_html((FIXTURES / "developer_site" / "index.html").read_text(), "https://developer.example/")
    assert {fact.value for fact in page.organization_names} >= {"Example Developers"}
    assert {(fact.metadata["platform"], fact.value) for fact in page.facts if "platform" in fact.metadata} == {
        ("facebook", "https://facebook.com/exampledevelopers"),
        ("instagram", "https://instagram.com/exampledevelopers"),
    }
    assert any(link.url == "https://developer.example/projects" and link.priority == 100 for link in page.links)
    assert not should_use_playwright(page)


def test_contacts_extract_phone_email_whatsapp_address_and_reject_share():
    page = parse_html((FIXTURES / "developer_site" / "contact.html").read_text(), "https://developer.example/contact")
    fields = {fact.field_name for fact in page.facts}
    assert {"sales_phone", "business_email", "whatsapp", "office_address", "official_linkedin"} <= fields
    assert not any("sharer" in fact.value for fact in page.facts)
    assert any(fact.metadata.get("normalized_value") == "+923001234567" for fact in page.facts)


def test_project_cards_extract_lahore_and_non_lahore_candidates():
    page = parse_html((FIXTURES / "developer_site" / "projects.html").read_text(), "https://developer.example/projects")
    projects = {fact.value: fact for fact in page.project_candidates}
    assert projects["Example Heights"].metadata["location_status"] == "confirmed_lahore"
    assert projects["Example Heights"].metadata["project_type"] == "apartments"
    assert projects["Example Heights"].metadata["project_status"] == "booking_open"
    assert projects["Capital Residency"].metadata["location_status"] == "unknown_location"
    assert all(fact.value != "View Project" for fact in page.project_candidates)


def test_application_shell_fallback_and_stable_content_hash():
    page = parse_html((FIXTURES / "javascript_site" / "index.html").read_text(), "https://developer.example/")
    assert should_use_playwright(page)
    assert content_hash("Hello   World") == content_hash(" hello world ")


def test_priority_exclusions():
    assert score_link("https://example.com/projects") == 100
    assert score_link("https://example.com/contact-us") == 80
    assert score_link("https://example.com/privacy") == 0


def test_explicit_developed_by_identity_has_priority_and_footer_junk_is_rejected():
    html = """
    <html><head><meta property="og:site_name" content="Autograph Apartments"></head>
    <body><p>Autograph has been developed by Concept Developers, a trusted name.</p>
    <footer>© 2026 All Rights Reserved</footer></body></html>
    """
    page = parse_html(html, "https://autograph.example/")
    assert page.organization_names[0].value == "Concept Developers"
    assert all(fact.value.casefold() != "all rights reserved" for fact in page.organization_names)
