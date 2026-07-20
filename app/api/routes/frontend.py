from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["Frontend"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "app_name": settings.app_name,
            "google_maps_browser_api_key": settings.google_maps_browser_api_key,
            "google_maps_configured": bool(settings.google_maps_browser_api_key),
            "google_maps_map_id": getattr(settings, "google_maps_map_id", ""),
        },
    )
