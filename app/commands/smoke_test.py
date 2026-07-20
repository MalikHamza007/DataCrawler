from __future__ import annotations

from uuid import uuid4

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Developer, Project
from app.schemas.export import ExportCreateRequest
from app.services.exports import create_export, generate_export_artifact


def main() -> int:
    run_id = f"smoke-{uuid4().hex[:8]}"
    settings = get_settings()
    with SessionLocal() as db:
        developer = Developer(name=f"{run_id} Developer", normalized_name=f"{run_id} developer")
        project = Project(name=f"{run_id} Project", normalized_name=f"{run_id} project", developer=developer, lahore_zone="Gulberg", review_status="approved")
        db.add_all([developer, project])
        db.flush()
        artifact = create_export(db, ExportCreateRequest(format="csv", scope="current_project_view", project_filters={"q": run_id}, filename_label=run_id), settings)
        db.commit()
        generate_export_artifact(db, artifact.id, settings)
        db.delete(project)
        db.delete(developer)
        db.commit()
    print(f"Smoke test passed: {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
