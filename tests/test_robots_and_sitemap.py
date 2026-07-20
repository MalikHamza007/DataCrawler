from app.collectors.websites.robots import is_allowed, parse_robots
from app.collectors.websites.sitemap import parse_sitemap


def test_robots_specific_group_longest_rule_and_sitemap():
    text = """User-agent: AlduorProjectDiscoveryBot\nDisallow: /projects\nAllow: /projects/public\nSitemap: https://example.com/sitemap.xml\nUser-agent: *\nDisallow: /\n"""
    rules, sitemaps = parse_robots(text, "AlduorProjectDiscoveryBot/0.1")
    assert not is_allowed(rules, "https://example.com/projects/private")
    assert is_allowed(rules, "https://example.com/projects/public/item")
    assert is_allowed(rules, "https://example.com/contact")
    assert sitemaps == ("https://example.com/sitemap.xml",)


def test_malformed_robots_keeps_valid_rules():
    rules, _ = parse_robots("bad line\nUser-agent: *\nDisallow: /private\nAllow: /private/public", "Bot")
    assert not is_allowed(rules, "https://example.com/private/x")
    assert is_allowed(rules, "https://example.com/private/public/x")


def test_sitemap_and_index_namespaces():
    urls, nested = parse_sitemap(b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/projects/a</loc></url></urlset>')
    assert urls == ["https://example.com/projects/a"] and nested == []
    urls, nested = parse_sitemap(b'<sitemapindex><sitemap><loc>https://example.com/projects.xml</loc></sitemap></sitemapindex>')
    assert urls == [] and nested == ["https://example.com/projects.xml"]
