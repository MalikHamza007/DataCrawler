from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LinkCandidate:
    url: str
    text: str
    priority: int


@dataclass(frozen=True)
class ExtractedFact:
    field_name: str
    value: str
    excerpt: str
    owner_hint: str = "uncertain"
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedPage:
    url: str
    title: str | None
    description: str | None
    canonical_tag: str | None
    text: str
    links: list[LinkCandidate]
    facts: list[ExtractedFact]
    organization_names: list[ExtractedFact]
    project_candidates: list[ExtractedFact]
    script_count: int
    app_shell_markers: int


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    content_type: str
    content: bytes
    headers: dict[str, str]


@dataclass(frozen=True)
class RobotsResult:
    status: str
    robots_url: str
    rules: "RobotsRules | None"
    sitemaps: tuple[str, ...] = ()
    warning: str | None = None


@dataclass(frozen=True)
class RobotsRule:
    allow: bool
    path: str


@dataclass
class RobotsRules:
    rules: list[RobotsRule] = field(default_factory=list)
    crawl_delay: float | None = None

    def allowed(self, url_path: str) -> bool:
        matches = [rule for rule in self.rules if url_path.startswith(rule.path)]
        if not matches:
            return True
        best_length = max(len(rule.path) for rule in matches)
        return any(rule.allow for rule in matches if len(rule.path) == best_length)
