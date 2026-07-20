from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import campaign_evidence, collection_jobs, contacts, dashboard, developers, entity_search, evidence, exports, extension, intelligence, map_config, map_projects, places, projects, refinement, social_captures, social_profiles, system, website_enrichment, worker_status

api_router = APIRouter()
api_router.include_router(developers.router)
api_router.include_router(projects.router)
api_router.include_router(contacts.router)
api_router.include_router(social_profiles.router)
api_router.include_router(evidence.router)
api_router.include_router(exports.router)
api_router.include_router(refinement.router)
api_router.include_router(campaign_evidence.router)
api_router.include_router(collection_jobs.router)
api_router.include_router(map_config.router)
api_router.include_router(map_projects.router)
api_router.include_router(places.router)
api_router.include_router(worker_status.router)
api_router.include_router(website_enrichment.router)
api_router.include_router(intelligence.router)
api_router.include_router(extension.router)
api_router.include_router(entity_search.router)
api_router.include_router(social_captures.router)
api_router.include_router(dashboard.router)
api_router.include_router(system.router)
