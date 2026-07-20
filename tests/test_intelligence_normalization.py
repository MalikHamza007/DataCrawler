import pytest

from app.intelligence.normalization import address_similarity, domain, haversine_meters, name_similarity, normalize_address, normalize_name_matching, normalize_name_storage, normalize_phone, normalize_social_url, normalize_url, phone_match


def test_name_normalization_and_similarity_are_deterministic():
    assert normalize_name_storage("  ABS Developers (Pvt.) Ltd. ") == "abs developers pvt ltd"
    assert normalize_name_matching("ABS Developers (Private) Limited") == "abs developers"
    assert name_similarity("ABS Developers Pvt Ltd", "ABS Developers (Private) Limited") >= 95
    assert name_similarity("ABC Developers", "ABC Properties") < 90


def test_pakistan_phone_normalization_preserves_original_and_matches():
    phone = normalize_phone("0300 1234567")
    assert phone.original == "0300 1234567" and phone.e164 == "+923001234567" and phone.valid
    assert normalize_phone("0092-300-1234567").e164 == "+923001234567"
    assert phone_match("0300 1234567", "+92 300 1234567") == "exact_valid_e164"
    assert normalize_phone("invalid").e164 is None


def test_url_domain_and_social_normalization():
    assert normalize_url("HTTPS://WWW.Example.COM:443/projects/?utm_source=x#top") == "https://example.com/projects"
    assert domain("https://www.example.com") == "example.com"
    assert normalize_social_url("https://m.facebook.com/ExampleDevelopers/?utm_source=x") == "https://facebook.com/ExampleDevelopers"
    assert normalize_social_url("https://facebook.com/sharer/sharer.php?u=x") is None
    assert normalize_social_url("https://instagram.com/example/p/123") is None


def test_address_and_coordinates():
    normalized = normalize_address("Plot 12, Gulberg III Boulevard, Block A")
    assert normalized == "plot 12 gulberg 3 blvd block a"
    assert address_similarity("Plot 12 Gulberg III Boulevard", "Plot 12, Gulberg 3 Blvd") >= 90
    assert haversine_meters(31.5, 74.3, 31.5, 74.3) == 0
    assert 90 < haversine_meters(31.5, 74.3, 31.5009, 74.3) < 110
    assert haversine_meters(None, None, 31.5, 74.3) is None
    with pytest.raises(ValueError): haversine_meters(100, 0, 0, 0)
