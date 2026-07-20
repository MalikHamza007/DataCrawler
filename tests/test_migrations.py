from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrade_downgrade_empty_database(tmp_path: Path) -> None:
    db_path = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stderr + upgrade.stdout
    assert db_path.exists()

    with sqlite3.connect(db_path) as connection:
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
    assert {"developers", "projects", "contacts", "social_profiles", "source_evidence", "collection_jobs", "collection_logs"}.issubset(tables)

    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert downgrade.returncode == 0, downgrade.stderr + downgrade.stdout

    upgrade_again = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert upgrade_again.returncode == 0, upgrade_again.stderr + upgrade_again.stdout
