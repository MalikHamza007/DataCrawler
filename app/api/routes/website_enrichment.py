from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DbSession
from app.schemas.collection_job import CollectionJobRead
from app.schemas.source_evidence import SourceEvidenceRead
from app.schemas.website_crawl import WebsiteCrawlRead, WebsitePageRead
from app.schemas.website_enrichment import ManualWebsiteEnrichmentRequest, WebsiteEnrichmentRequest, WebsitePreviewRequest, WebsitePreviewResponse
from app.services import website_enrichment as service
from app.collectors.websites.exceptions import UnsafeURLError

router = APIRouter(tags=["Website Enrichment"])


@router.post("/website-enrichment-jobs", response_model=CollectionJobRead, status_code=status.HTTP_201_CREATED)
def create_manual_job(payload: ManualWebsiteEnrichmentRequest, db: DbSession) -> object:
    try:
        return service.create_manual_job(db, payload)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/website-enrichment/preview", response_model=WebsitePreviewResponse)
def preview(payload: WebsitePreviewRequest) -> dict:
    try:
        return service.preview(payload)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/website-crawls/{crawl_id}", response_model=WebsiteCrawlRead)
def get_crawl(crawl_id: int, db: DbSession) -> object:
    return service.get_crawl(db, crawl_id)


@router.get("/website-crawls/{crawl_id}/pages", response_model=list[WebsitePageRead])
def get_pages(crawl_id: int, db: DbSession) -> list[object]:
    return service.list_pages(db, crawl_id)


@router.get("/website-crawls/{crawl_id}/evidence", response_model=list[SourceEvidenceRead])
def get_evidence(crawl_id: int, db: DbSession) -> list[object]:
    return service.list_evidence(db, crawl_id)


@router.post("/projects/{project_id}/website-enrichment-jobs", response_model=CollectionJobRead, status_code=status.HTTP_201_CREATED)
def create_project_job(project_id: int, payload: WebsiteEnrichmentRequest, db: DbSession) -> object:
    try:
        return service.create_project_job(db, project_id, payload)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/developers/{developer_id}/website-enrichment-jobs", response_model=CollectionJobRead, status_code=status.HTTP_201_CREATED)
def create_developer_job(developer_id: int, payload: WebsiteEnrichmentRequest, db: DbSession) -> object:
    try:
        return service.create_developer_job(db, developer_id, payload)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
