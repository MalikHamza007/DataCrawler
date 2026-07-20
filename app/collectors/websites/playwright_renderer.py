from __future__ import annotations

from collections.abc import Callable

from app.collectors.websites.security import is_same_site, validate_url_dns
from app.core.config import Settings


class PlaywrightRenderer:
    def __init__(self, settings: Settings, validator: Callable[[str], str] = validate_url_dns) -> None:
        self.settings = settings
        self.validator = validator

    def render(self, url: str, *, seed_url: str, allow_subdomains: bool, cancellation_check: Callable[[], None] | None = None) -> str:
        from playwright.sync_api import sync_playwright

        self.validator(url)
        if cancellation_check:
            cancellation_check()
        with sync_playwright() as playwright:
            browser_type = getattr(playwright, self.settings.website_crawler_playwright_browser)
            browser = browser_type.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            def route_request(route: object) -> None:
                request = route.request
                if request.resource_type in {"image", "media", "font", "websocket", "eventsource"}:
                    route.abort()
                    return
                try:
                    self.validator(request.url)
                    if not is_same_site(request.url, seed_url, allow_subdomains):
                        route.abort()
                    else:
                        route.continue_()
                except Exception:
                    route.abort()

            page.route("**/*", route_request)
            page.goto(url, wait_until="domcontentloaded", timeout=int(self.settings.website_crawler_playwright_timeout_seconds * 1000))
            html = page.content()
            page.close()
            context.close()
            browser.close()
        if cancellation_check:
            cancellation_check()
        return html
