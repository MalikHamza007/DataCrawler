from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors.google_places.client import GooglePlacesClient
from app.collectors.google_places.exceptions import GooglePlacesError
from app.collectors.google_places.geometry import circle_to_google_restriction, point_in_polygon
from app.collectors.google_places.normalizer import normalize_place
from app.collectors.google_places.service import build_search_plan
from app.collectors.google_places.types import NormalizedPlaceCandidate, SearchPlan
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, EntityNotFoundError
from app.db.base import utc_now
from app.models.collection_job import CollectionJob, CollectionLog
from app.models.contact import Contact
from app.models.project import Project
from app.models.project_discovery import ProjectDiscovery
from app.models.source_evidence import SourceEvidence
from app.schemas.map_config import MapPoint, ProjectSearchConfig
from app.schemas.places import PlacesDiscoveryResult, SearchPlanRead
from app.services.collection_jobs import get_collection_job
from app.services.normalization import normalize_contact_value, normalize_name


def places_status(settings: Settings | None = None) -> dict[str, bool]:
    settings = settings or get_settings()
    configured = bool(settings.google_places_server_api_key)
    return {
        "enabled": settings.google_places_enabled,
        "configured": configured,
        "dry_run": settings.google_places_dry_run,
        "text_search_available": settings.google_places_enabled and configured,
        "nearby_search_available": settings.google_places_enabled and configured and settings.google_places_enable_nearby_search,
        "details_enrichment_enabled": settings.google_places_enable_details_enrichment,
    }


def preview_places_plan(db: Session, job_id: int, settings: Settings | None = None) -> SearchPlanRead:
    job = _get_places_job(db, job_id)
    config = ProjectSearchConfig.model_validate(job.search_config_json)
    plan = build_search_plan(job.id, config, settings or get_settings())
    return _plan_read(plan)


def discover_places_for_job(
    db: Session,
    job_id: int,
    *,
    client: GooglePlacesClient | None = None,
    settings: Settings | None = None,
    progress_callback: object | None = None,
    heartbeat_callback: object | None = None,
    cancellation_check: object | None = None,
    manage_status: bool = True,
) -> PlacesDiscoveryResult:
    settings = settings or get_settings()
    job = _get_places_job(db, job_id)
    if job.status not in {"queued", "failed", "running"}:
        raise ConflictError(f"Collection job {job.id} cannot run discovery from status {job.status}.")
    if job.status == "running" and manage_status:
        raise ConflictError(f"Collection job {job.id} is already running.")
    config = ProjectSearchConfig.model_validate(job.search_config_json)
    plan = build_search_plan(job.id, config, settings)
    _log(db, job.id, "info", "Search plan generated", {"query_count": len(plan.queries), "cell_count": len(plan.cells)})
    _call(progress_callback, phase="planning", message="Search plan generated", total_items=plan.estimated_max_pages + len(plan.nearby_specs))

    if settings.google_places_dry_run:
        if manage_status:
            job.status = "completed"
            job.completed_at = utc_now()
            job.progress_phase = "completed"
            job.progress_message = "Dry-run search plan completed"
            job.total_items = plan.estimated_max_pages + len(plan.nearby_specs)
            job.processed_items = job.total_items
            job.execution_summary_json = {"dry_run": True, "estimated_max_requests": plan.estimated_max_requests}
            db.commit()
        return PlacesDiscoveryResult(
            job_id=job.id,
            status=job.status,
            requests_made=0,
            retry_count=0,
            raw_results=0,
            unique_place_ids=0,
            projects_created=0,
            projects_updated=0,
            contacts_created=0,
            websites_discovered=0,
            duplicates_skipped=0,
            results_outside_geometry=0,
            dry_run=True,
        )

    raw_results = 0
    unique_place_ids: set[str] = set()
    projects_created = 0
    projects_updated = 0
    duplicates_skipped = 0
    outside_geometry = 0
    contacts_created = 0
    website_project_ids: set[int] = set()

    try:
        client = client or GooglePlacesClient(settings=settings)
        if manage_status:
            job.status = "running"
            job.started_at = utc_now()
            job.error_message = None
            db.commit()

        for query_spec in plan.queries:
            _call(cancellation_check)
            _call(heartbeat_callback)
            _call(progress_callback, phase="searching", message=f"Processing query {query_spec.query}", total_items=plan.estimated_max_pages + len(plan.nearby_specs))
            page_token = None
            base_body = {
                "textQuery": query_spec.query,
                "pageSize": settings.google_places_text_page_size,
                "languageCode": settings.google_places_default_language_code,
                "regionCode": settings.google_places_default_region_code,
                "locationRestriction": query_spec.location_restriction,
            }
            for page_number in range(1, settings.google_places_max_pages_per_query + 1):
                _call(cancellation_check)
                _call(heartbeat_callback)
                body = dict(base_body)
                if page_token:
                    body["pageToken"] = page_token
                _log(db, job.id, "info", "Google Text Search started", {"query": query_spec.query, "cell_id": query_spec.cell_id, "page": page_number})
                response = client.text_search(body)
                _call(heartbeat_callback)
                places = response.get("places") or []
                raw_results += len(places)
                _call(progress_callback, phase="normalizing", message=f"Normalizing {len(places)} Google Place results", processed_delta=1)
                _log(db, job.id, "info", "Google Text Search page received", {"query": query_spec.query, "cell_id": query_spec.cell_id, "page": page_number, "result_count": len(places), "next_page_present": bool(response.get("nextPageToken"))})
                for place in places:
                    _call(cancellation_check)
                    candidate = normalize_place(place, source_method="text_search", source_query=query_spec.query, source_cell_id=query_spec.cell_id)
                    if _outside_polygon(config, candidate):
                        outside_geometry += 1
                        _log(db, job.id, "debug", "Result discarded outside polygon", {"google_place_id": candidate.google_place_id})
                        continue
                    if candidate.google_place_id in unique_place_ids:
                        duplicates_skipped += 1
                    else:
                        unique_place_ids.add(candidate.google_place_id)
                    created, updated, new_contacts, project_id = _persist_candidate(db, job, candidate)
                    projects_created += int(created)
                    projects_updated += int(updated)
                    contacts_created += new_contacts
                    if candidate.website_url:
                        website_project_ids.add(project_id)
                    _call(progress_callback, phase="persisting", message="Saving project candidates", created_delta=int(created), updated_delta=int(updated))
                    if len(unique_place_ids) >= settings.google_places_max_results_per_job:
                        break
                page_token = response.get("nextPageToken")
                if not page_token or len(unique_place_ids) >= settings.google_places_max_results_per_job:
                    break

        for nearby_spec in plan.nearby_specs:
            _call(cancellation_check)
            _call(heartbeat_callback)
            body = {
                "includedTypes": [nearby_spec.included_type],
                "maxResultCount": min(settings.google_places_text_page_size, 20),
                "locationRestriction": circle_to_google_restriction(nearby_spec.center, nearby_spec.radius_meters),
                "rankPreference": "POPULARITY",
                "languageCode": settings.google_places_default_language_code,
                "regionCode": settings.google_places_default_region_code,
            }
            _log(db, job.id, "info", "Google Nearby Search started", {"included_type": nearby_spec.included_type, "cell_id": nearby_spec.cell_id})
            response = client.nearby_search(body)
            _call(progress_callback, phase="searching", message=f"Processing Nearby Search {nearby_spec.included_type}", processed_delta=1)
            places = response.get("places") or []
            raw_results += len(places)
            for place in places:
                candidate = normalize_place(place, source_method="nearby_search", source_query=nearby_spec.included_type, source_cell_id=nearby_spec.cell_id)
                if candidate.google_place_id in unique_place_ids:
                    duplicates_skipped += 1
                else:
                    unique_place_ids.add(candidate.google_place_id)
                created, updated, new_contacts, project_id = _persist_candidate(db, job, candidate)
                projects_created += int(created)
                projects_updated += int(updated)
                contacts_created += new_contacts
                if candidate.website_url:
                    website_project_ids.add(project_id)
                _call(progress_callback, phase="persisting", message="Saving project candidates", created_delta=int(created), updated_delta=int(updated))

        job.total_items = raw_results
        job.processed_items = len(unique_place_ids)
        job.created_items = projects_created
        job.updated_items = projects_updated
        job.failed_items = outside_geometry
        job.execution_summary_json = {
            "api_requests": client.request_count,
            "raw_results": raw_results,
            "unique_place_ids": len(unique_place_ids),
            "duplicates_skipped": duplicates_skipped,
            "results_outside_geometry": outside_geometry,
            "projects_created": projects_created,
            "projects_updated": projects_updated,
            "contacts_created": contacts_created,
            "websites_discovered": len(website_project_ids),
            "retry_count": client.retry_count,
        }
        if manage_status:
            job.status = "completed"
            job.completed_at = utc_now()
            job.progress_phase = "completed"
            job.progress_message = "Collection completed"
        db.commit()
        _log(db, job.id, "info", "Google Places discovery completed", {"projects_created": projects_created, "projects_updated": projects_updated})
        return PlacesDiscoveryResult(
            job_id=job.id,
            status=job.status,
            requests_made=client.request_count,
            retry_count=client.retry_count,
            raw_results=raw_results,
            unique_place_ids=len(unique_place_ids),
            projects_created=projects_created,
            projects_updated=projects_updated,
            contacts_created=contacts_created,
            websites_discovered=len(website_project_ids),
            duplicates_skipped=duplicates_skipped,
            results_outside_geometry=outside_geometry,
        )
    except Exception as exc:
        if manage_status:
            job.status = "failed"
            job.completed_at = utc_now()
            job.error_message = _safe_error_message(exc)
            job.progress_phase = "failed"
            job.progress_message = "Collection failed"
            db.commit()
            _log(db, job.id, "error", "Google Places discovery failed", {"error": job.error_message})
        raise


def _get_places_job(db: Session, job_id: int) -> CollectionJob:
    job = get_collection_job(db, job_id)
    if job.job_type != "places_discovery":
        raise ConflictError("Only places_discovery jobs can use Google Places discovery.")
    return job


def _persist_candidate(db: Session, job: CollectionJob, candidate: NormalizedPlaceCandidate) -> tuple[bool, bool, int, int]:
    project = db.scalar(select(Project).where(Project.google_place_id == candidate.google_place_id))
    created = False
    updated = False
    if project is None:
        project = Project(
            developer_id=None,
            name=candidate.display_name,
            normalized_name=normalize_name(candidate.display_name),
            address=candidate.formatted_address,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            google_place_id=candidate.google_place_id,
            google_maps_url=candidate.google_maps_url,
            official_website_url=candidate.website_url,
            city="Lahore",
            country="Pakistan",
            verification_status="unverified",
            project_status="unknown",
        )
        db.add(project)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            project = db.scalar(select(Project).where(Project.google_place_id == candidate.google_place_id))
            if project is None:
                raise
        else:
            db.refresh(project)
            created = True
    else:
        updated = _safe_update_project(project, candidate)
        if updated:
            db.commit()
            db.refresh(project)
    _record_discovery(db, project, job.id, candidate)
    contacts_created = _record_place_contacts(db, project, candidate)
    _record_evidence(db, project, job.id, candidate)
    if created:
        _log(db, job.id, "info", "Project candidate created", {"project_id": project.id, "google_place_id": candidate.google_place_id})
    else:
        _log(db, job.id, "info", "Existing Google Place ID encountered", {"project_id": project.id, "google_place_id": candidate.google_place_id})
    return created, updated, contacts_created, project.id


def _safe_update_project(project: Project, candidate: NormalizedPlaceCandidate) -> bool:
    changed = False
    for attr, value in {
        "address": candidate.formatted_address,
        "latitude": candidate.latitude,
        "longitude": candidate.longitude,
        "google_maps_url": candidate.google_maps_url,
        "official_website_url": candidate.website_url,
    }.items():
        if getattr(project, attr) in (None, "") and value not in (None, ""):
            setattr(project, attr, value)
            changed = True
    return changed


def _record_discovery(db: Session, project: Project, job_id: int, candidate: NormalizedPlaceCandidate) -> None:
    discovery = ProjectDiscovery(
        project_id=project.id,
        collection_job_id=job_id,
        source="google_places",
        source_method=candidate.source_method,
        source_query=candidate.source_query,
        source_cell_id=candidate.source_cell_id,
        google_primary_type=candidate.primary_type,
        google_types_json=candidate.types,
        google_business_status=candidate.business_status,
        encounter_count=1,
    )
    db.add(discovery)
    db.commit()


def _record_evidence(db: Session, project: Project, job_id: int, candidate: NormalizedPlaceCandidate) -> None:
    existing = db.scalar(select(SourceEvidence.id).where(SourceEvidence.project_id == project.id, SourceEvidence.collection_job_id == job_id, SourceEvidence.field_name == "project_candidate"))
    if existing:
        return
    summary = f"{candidate.display_name}; address={candidate.formatted_address}; place_id={candidate.google_place_id}"
    db.add(
        SourceEvidence(
            project_id=project.id,
            collection_job_id=job_id,
            source_type="google_places",
            source_url=candidate.google_maps_url or f"https://www.google.com/maps/place/?q=place_id:{candidate.google_place_id}",
            source_title=candidate.display_name,
            captured_text=summary[:20000],
            field_name="project_candidate",
            extracted_value=candidate.display_name,
            verification_status="unverified",
        )
    )
    db.commit()


def _record_place_contacts(db: Session, project: Project, candidate: NormalizedPlaceCandidate) -> int:
    value = candidate.international_phone_number or candidate.national_phone_number
    if not value:
        return 0
    normalized = normalize_contact_value(value, "phone")
    exists = db.scalar(select(Contact.id).where(Contact.project_id == project.id, Contact.contact_type == "phone", Contact.normalized_value == normalized))
    if exists:
        return 0
    db.add(Contact(project_id=project.id, contact_type="phone", value=value, normalized_value=normalized, is_public_business_contact=True, verification_status="unverified", source_url=candidate.google_maps_url))
    db.commit()
    return 1


def _outside_polygon(config: ProjectSearchConfig, candidate: NormalizedPlaceCandidate) -> bool:
    if config.search_mode != "polygon" or candidate.latitude is None or candidate.longitude is None:
        return False
    assert config.geometry is not None and config.geometry.coordinates is not None
    return not point_in_polygon(MapPoint(lat=candidate.latitude, lng=candidate.longitude), config.geometry.coordinates)


def _log(db: Session, job_id: int, level: str, message: str, context: dict | None = None) -> None:
    db.add(CollectionLog(collection_job_id=job_id, level=level, message=message, context_json=context or {}))
    db.commit()


def _plan_read(plan: SearchPlan) -> SearchPlanRead:
    return SearchPlanRead(
        job_id=plan.job_id,
        search_mode=plan.search_mode,
        cell_count=len(plan.cells),
        query_count=len(plan.queries),
        nearby_request_count=len(plan.nearby_specs),
        estimated_max_pages=plan.estimated_max_pages,
        estimated_max_requests=plan.estimated_max_requests,
        estimated_max_results=plan.estimated_max_results,
        selected_project_types=plan.selected_project_types,
        queries=[{"query": query.query, "cell_id": query.cell_id} for query in plan.queries],
    )


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, GooglePlacesError):
        return str(exc)
    return "Google Places discovery failed."


def _call(callback: object | None, **kwargs: object) -> None:
    if callback is None:
        return
    callback(**kwargs)
