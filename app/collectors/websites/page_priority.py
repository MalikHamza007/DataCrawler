from app.collectors.websites.types import LinkCandidate

VERY_HIGH = ("projects", "our-projects", "developments", "portfolio", "properties", "residential", "commercial", "mixed-use")
HIGH = ("contact", "about", "company", "who-we-are", "team", "leadership", "management", "directors")
MEDIUM = ("news", "media", "press", "updates", "construction-updates")
EXCLUDED = ("privacy", "terms", "cookies", "login", "register", "cart", "checkout", "account", "search", "tag", "author", "feed", "wp-admin", "wp-login")


def score_link(url: str, anchor_text: str = "") -> int:
    value = f"{url} {anchor_text}".lower()
    if any(term in value for term in EXCLUDED):
        return 0
    if any(term in value for term in VERY_HIGH):
        return 100
    if any(term in value for term in HIGH):
        return 80
    if any(term in value for term in MEDIUM):
        return 50
    return 10


def prioritize_links(links: list[LinkCandidate], limit: int) -> list[LinkCandidate]:
    unique: dict[str, LinkCandidate] = {}
    for link in links:
        if link.priority > 0 and (link.url not in unique or link.priority > unique[link.url].priority):
            unique[link.url] = link
    return sorted(unique.values(), key=lambda item: (-item.priority, item.url))[:limit]
