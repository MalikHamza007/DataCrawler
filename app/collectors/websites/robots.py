from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.collectors.websites.types import RobotsRule, RobotsRules


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[RobotsRule] = field(default_factory=list)
    crawl_delay: float | None = None


def parse_robots(text: str, user_agent: str) -> tuple[RobotsRules, tuple[str, ...]]:
    groups: list[_Group] = []
    current: _Group | None = None
    sitemaps: list[str] = []
    has_rules = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.casefold()
        if key == "sitemap" and value:
            sitemaps.append(value)
            continue
        if key == "user-agent":
            if current is None or has_rules:
                current = _Group()
                groups.append(current)
                has_rules = False
            current.agents.append(value.casefold())
        elif current and key in {"allow", "disallow"}:
            has_rules = True
            if value:
                current.rules.append(RobotsRule(key == "allow", value.split("*", 1)[0].rstrip("$") or "/"))
        elif current and key == "crawl-delay":
            try:
                current.crawl_delay = max(0.0, float(value))
            except ValueError:
                pass
    token = user_agent.split("/", 1)[0].casefold()
    specific = [group for group in groups if any(agent != "*" and agent in token for agent in group.agents)]
    selected = specific or [group for group in groups if "*" in group.agents]
    return RobotsRules([rule for group in selected for rule in group.rules], max((group.crawl_delay or 0 for group in selected), default=0) or None), tuple(dict.fromkeys(sitemaps))


def is_allowed(rules: RobotsRules | None, url: str) -> bool:
    if rules is None:
        return True
    parts = urlsplit(url)
    return rules.allowed(parts.path + (("?" + parts.query) if parts.query else ""))
