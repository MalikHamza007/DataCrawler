from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Alduor Lahore Project Discovery Agent"
    app_env: str = "development"
    debug: bool = True
    docs_enabled: bool = True
    database_url: str = "sqlite:///./alduor.db"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    allowed_hosts: list[str] = ["127.0.0.1", "localhost", "testserver"]
    max_request_body_bytes: int = 1_048_576
    google_maps_browser_api_key: str = ""
    google_maps_map_id: str = ""
    google_places_server_api_key: str = ""
    google_places_api_base_url: str = "https://places.googleapis.com/v1"
    google_places_enabled: bool = False
    google_places_timeout_seconds: float = 20
    google_places_max_retries: int = 3
    google_places_text_page_size: int = 20
    google_places_max_pages_per_query: int = 3
    google_places_max_queries_per_job: int = 100
    google_places_max_results_per_job: int = 1000
    google_places_default_language_code: str = "en"
    google_places_default_region_code: str = "PK"
    google_places_enable_nearby_search: bool = True
    google_places_enable_details_enrichment: bool = False
    google_places_request_delay_ms: int = 200
    google_places_dry_run: bool = False
    area_research_auto_enrich_websites: bool = True
    area_research_max_websites: int = 20
    area_research_max_pages_per_website: int = 10
    refinement_max_websites: int = 250
    refinement_max_pages_per_website: int = 10
    places_grid_cell_radius_meters: int = 3000
    places_grid_max_cells: int = 100
    places_grid_overlap_percent: int = 10
    worker_enabled: bool = True
    worker_name: str = "alduor-local-collector"
    worker_poll_interval_seconds: float = 2
    worker_heartbeat_interval_seconds: float = 10
    worker_lease_seconds: int = 60
    worker_job_lease_seconds: int = 90
    worker_stale_job_grace_seconds: int = 30
    worker_shutdown_grace_seconds: int = 30
    worker_max_job_attempts: int = 3
    worker_retry_base_delay_seconds: int = 10
    worker_retry_max_delay_seconds: int = 300
    worker_supported_job_types: list[str] = ["places_discovery", "website_enrichment", "classification_analysis", "duplicate_scan", "export_generation"]
    worker_progress_log_interval_seconds: int = 5
    sqlite_busy_timeout_ms: int = 5000
    sqlite_journal_mode: str = "WAL"
    website_crawler_enabled: bool = True
    website_crawler_user_agent: str = "AlduorProjectDiscoveryBot/0.1"
    website_crawler_contact_url: str = "https://alduor.com"
    website_crawler_timeout_seconds: float = 15
    website_crawler_connect_timeout_seconds: float = 10
    website_crawler_max_redirects: int = 5
    website_crawler_max_pages_per_site: int = 25
    website_crawler_max_depth: int = 3
    website_crawler_max_response_bytes: int = 5_000_000
    website_crawler_max_sitemaps: int = 5
    website_crawler_max_sitemap_urls: int = 500
    website_crawler_max_links_per_page: int = 200
    website_crawler_min_request_delay_ms: int = 1000
    website_crawler_max_request_delay_ms: int = 3000
    website_crawler_robots_cache_hours: int = 24
    website_crawler_max_retries: int = 2
    website_crawler_allow_subdomains: bool = False
    website_crawler_enable_playwright: bool = True
    website_crawler_playwright_max_pages: int = 5
    website_crawler_playwright_timeout_seconds: float = 20
    website_crawler_playwright_browser: str = "chromium"
    website_crawler_store_raw_html: bool = False
    website_crawler_debug_screenshots: bool = False
    website_crawler_max_text_length: int = 200_000
    website_crawler_max_evidence_excerpt_length: int = 2000
    website_crawler_max_emails_per_site: int = 20
    website_crawler_max_phones_per_site: int = 30
    website_crawler_max_projects_per_site: int = 200
    website_crawler_respect_robots: bool = True
    intelligence_enabled: bool = True
    intelligence_rule_version: str = "m6-v1"
    classification_developer_verified_threshold: int = 80
    classification_developer_probable_threshold: int = 60
    classification_manual_review_threshold: int = 40
    classification_project_verified_threshold: int = 80
    classification_project_probable_threshold: int = 60
    relationship_verified_suggestion_threshold: int = 80
    relationship_probable_threshold: int = 60
    duplicate_candidate_threshold: int = 55
    duplicate_high_confidence_threshold: int = 80
    duplicate_max_candidates_per_scan: int = 5000
    duplicate_batch_size: int = 250
    name_similarity_high_threshold: int = 90
    name_similarity_medium_threshold: int = 80
    name_similarity_low_threshold: int = 70
    project_duplicate_distance_high_meters: float = 75
    project_duplicate_distance_medium_meters: float = 250
    project_duplicate_distance_max_meters: float = 2000
    developer_duplicate_max_pair_comparisons: int = 100_000
    project_duplicate_max_pair_comparisons: int = 200_000
    alduor_extension_api_token: str = ""
    alduor_extension_allowed_origins: list[str] = []
    alduor_extension_enabled: bool = True
    alduor_extension_max_capture_bytes: int = 100_000
    alduor_extension_max_text_length: int = 20_000
    alduor_extension_max_links: int = 100
    alduor_extension_max_contacts: int = 30
    dashboard_map_max_points: int = 2000
    export_enabled: bool = True
    export_directory: str = "./data/exports"
    export_max_rows: int = 50_000
    export_max_file_bytes: int = 104_857_600
    export_batch_size: int = 500
    export_retention_hours: int = 168
    export_max_active_jobs: int = 3
    export_excel_max_cell_characters: int = 32_000
    export_csv_encoding: str = "utf-8-sig"
    export_json_indent: int = 2
    export_formula_protection: bool = True
    export_include_evidence_default: bool = False
    export_include_logs_default: bool = False
    export_validate_files: bool = True
    export_delete_temp_files: bool = True
    backup_enabled: bool = True
    backup_directory: str = "./data/backups"
    backup_retention_days: int = 30
    backup_max_count: int = 50
    backup_include_exports: bool = False
    log_level: str = "INFO"
    log_format: str = "text"
    log_to_stdout: bool = True
    log_to_file: bool = False
    log_directory: str = "./data/logs"
    log_file_max_bytes: int = 10_485_760
    log_file_backup_count: int = 5
    log_include_access_log: bool = True
    min_free_disk_bytes: int = 1_073_741_824

    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            if value.strip().startswith("["):
                import json

                return list(json.loads(value))
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            if value.strip().startswith("["):
                import json

                return list(json.loads(value))
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("worker_supported_job_types", mode="before")
    @classmethod
    def parse_worker_job_types(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("alduor_extension_allowed_origins", mode="before")
    @classmethod
    def parse_extension_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_google_places_settings(self) -> "Settings":
        if self.google_places_timeout_seconds <= 0:
            raise ValueError("GOOGLE_PLACES_TIMEOUT_SECONDS must be greater than zero")
        if not 1 <= self.google_places_text_page_size <= 20:
            raise ValueError("GOOGLE_PLACES_TEXT_PAGE_SIZE must be between 1 and 20")
        if self.google_places_max_retries < 1:
            raise ValueError("GOOGLE_PLACES_MAX_RETRIES must be at least 1")
        if self.google_places_max_queries_per_job < 1:
            raise ValueError("GOOGLE_PLACES_MAX_QUERIES_PER_JOB must be at least 1")
        if self.google_places_max_results_per_job < 1:
            raise ValueError("GOOGLE_PLACES_MAX_RESULTS_PER_JOB must be at least 1")
        if self.places_grid_max_cells < 1:
            raise ValueError("PLACES_GRID_MAX_CELLS must be at least 1")
        if self.worker_poll_interval_seconds <= 0:
            raise ValueError("WORKER_POLL_INTERVAL_SECONDS must be greater than zero")
        if self.worker_heartbeat_interval_seconds <= 0 or self.worker_heartbeat_interval_seconds >= self.worker_lease_seconds:
            raise ValueError("WORKER_HEARTBEAT_INTERVAL_SECONDS must be greater than zero and shorter than WORKER_LEASE_SECONDS")
        if self.worker_job_lease_seconds <= self.worker_heartbeat_interval_seconds:
            raise ValueError("WORKER_JOB_LEASE_SECONDS must be longer than WORKER_HEARTBEAT_INTERVAL_SECONDS")
        if not 1 <= self.worker_max_job_attempts <= 10:
            raise ValueError("WORKER_MAX_JOB_ATTEMPTS must be between 1 and 10")
        if self.worker_retry_base_delay_seconds <= 0 or self.worker_retry_max_delay_seconds <= 0:
            raise ValueError("Worker retry delays must be positive")
        if self.sqlite_busy_timeout_ms < 0:
            raise ValueError("SQLITE_BUSY_TIMEOUT_MS must not be negative")
        if not 1 <= self.website_crawler_max_pages_per_site <= 200:
            raise ValueError("WEBSITE_CRAWLER_MAX_PAGES_PER_SITE must be between 1 and 200")
        if not 0 <= self.website_crawler_max_depth <= 10:
            raise ValueError("WEBSITE_CRAWLER_MAX_DEPTH must be between 0 and 10")
        if self.website_crawler_min_request_delay_ms < 0 or self.website_crawler_max_request_delay_ms < 0:
            raise ValueError("Website crawler request delays must not be negative")
        if self.website_crawler_min_request_delay_ms > self.website_crawler_max_request_delay_ms:
            raise ValueError("Website crawler minimum delay cannot exceed maximum delay")
        if self.website_crawler_playwright_max_pages > self.website_crawler_max_pages_per_site:
            raise ValueError("Playwright page limit cannot exceed total page limit")
        if self.website_crawler_max_redirects < 0 or self.website_crawler_max_retries < 0:
            raise ValueError("Website crawler redirect and retry limits must not be negative")
        if self.website_crawler_max_response_bytes < 1 or self.website_crawler_max_links_per_page < 1:
            raise ValueError("Website crawler response and link limits must be positive")
        score_fields = (
            self.classification_developer_verified_threshold, self.classification_developer_probable_threshold,
            self.classification_manual_review_threshold, self.classification_project_verified_threshold,
            self.classification_project_probable_threshold, self.relationship_verified_suggestion_threshold,
            self.relationship_probable_threshold, self.duplicate_candidate_threshold,
            self.duplicate_high_confidence_threshold, self.name_similarity_high_threshold,
            self.name_similarity_medium_threshold, self.name_similarity_low_threshold,
        )
        if any(value < 0 or value > 100 for value in score_fields):
            raise ValueError("Intelligence score thresholds must be between 0 and 100")
        if not self.name_similarity_high_threshold > self.name_similarity_medium_threshold > self.name_similarity_low_threshold:
            raise ValueError("Name similarity thresholds must be ordered high > medium > low")
        if self.duplicate_candidate_threshold > self.duplicate_high_confidence_threshold:
            raise ValueError("Duplicate candidate threshold cannot exceed high confidence threshold")
        if self.duplicate_batch_size <= 0 or self.duplicate_max_candidates_per_scan <= 0:
            raise ValueError("Duplicate batch and candidate limits must be positive")
        if self.developer_duplicate_max_pair_comparisons <= 0 or self.project_duplicate_max_pair_comparisons <= 0:
            raise ValueError("Duplicate pair limits must be positive")
        if not 0 < self.project_duplicate_distance_high_meters < self.project_duplicate_distance_medium_meters < self.project_duplicate_distance_max_meters:
            raise ValueError("Project distance thresholds must be positive and ordered")
        if self.alduor_extension_enabled and self.app_env != "development" and not self.alduor_extension_api_token:
            raise ValueError("ALDUOR_EXTENSION_API_TOKEN must be set when the extension is enabled outside development")
        if self.alduor_extension_max_capture_bytes < 1000:
            raise ValueError("ALDUOR_EXTENSION_MAX_CAPTURE_BYTES must be at least 1000")
        if self.alduor_extension_max_text_length < 1000:
            raise ValueError("ALDUOR_EXTENSION_MAX_TEXT_LENGTH must be at least 1000")
        if self.alduor_extension_max_links < 1 or self.alduor_extension_max_contacts < 1:
            raise ValueError("Extension link and contact limits must be positive")
        if self.dashboard_map_max_points < 1:
            raise ValueError("DASHBOARD_MAP_MAX_POINTS must be positive")
        if self.app_env not in {"development", "test", "release"}:
            raise ValueError("APP_ENV must be development, test or release")
        if self.max_request_body_bytes < 1024:
            raise ValueError("MAX_REQUEST_BODY_BYTES must be at least 1024")
        if self.app_env == "release" and "*" in self.cors_origins:
            raise ValueError("Wildcard CORS is not allowed in release mode")
        if self.app_env == "release" and self.debug:
            raise ValueError("DEBUG must be false in release mode")
        if self.app_env == "release" and self.google_places_enabled and not self.google_places_server_api_key:
            raise ValueError("GOOGLE_PLACES_SERVER_API_KEY is required when Google Places is enabled")
        if self.google_maps_map_id and not self.google_maps_browser_api_key:
            raise ValueError("GOOGLE_MAPS_BROWSER_API_KEY is required when GOOGLE_MAPS_MAP_ID is set")
        if self.area_research_max_websites < 0 or self.area_research_max_pages_per_website < 1:
            raise ValueError("Area research website limits are invalid")
        if not 1 <= self.refinement_max_websites <= 1000 or not 1 <= self.refinement_max_pages_per_website <= 50:
            raise ValueError("Refinement website limits are invalid")
        if not self.export_directory.strip():
            raise ValueError("EXPORT_DIRECTORY cannot be empty")
        if self.export_max_rows <= 0 or self.export_max_file_bytes <= 0:
            raise ValueError("Export row and file limits must be positive")
        if not 1 <= self.export_batch_size <= 5000:
            raise ValueError("EXPORT_BATCH_SIZE must be between 1 and 5000")
        if self.export_retention_hours <= 0:
            raise ValueError("EXPORT_RETENTION_HOURS must be positive")
        if not 1 <= self.export_max_active_jobs <= 20:
            raise ValueError("EXPORT_MAX_ACTIVE_JOBS must be between 1 and 20")
        if not 1 <= self.export_excel_max_cell_characters <= 32767:
            raise ValueError("EXPORT_EXCEL_MAX_CELL_CHARACTERS must be between 1 and 32767")
        if self.export_csv_encoding not in {"utf-8-sig", "utf-8"}:
            raise ValueError("EXPORT_CSV_ENCODING must be utf-8-sig or utf-8")
        if not 0 <= self.export_json_indent <= 8:
            raise ValueError("EXPORT_JSON_INDENT must be between 0 and 8")
        if not self.backup_directory.strip():
            raise ValueError("BACKUP_DIRECTORY cannot be empty")
        if self.backup_retention_days <= 0 or self.backup_max_count <= 0:
            raise ValueError("Backup retention limits must be positive")
        if not self.log_directory.strip():
            raise ValueError("LOG_DIRECTORY cannot be empty")
        if self.log_file_max_bytes <= 0 or self.log_file_backup_count < 0:
            raise ValueError("Log rotation settings are invalid")
        if self.log_format not in {"json", "text"}:
            raise ValueError("LOG_FORMAT must be json or text")
        if self.min_free_disk_bytes < 0:
            raise ValueError("MIN_FREE_DISK_BYTES must not be negative")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
