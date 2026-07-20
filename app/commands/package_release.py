from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

from app.commands._ops import app_version, sha256


EXCLUDES = {".git", ".venv", "venv", ".pytest_cache", "__pycache__", ".env", "data"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the local MVP release.")
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = root / args.output_dir
    output.mkdir(exist_ok=True)
    archive = output / f"alduor-project-discovery-{app_version()}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            rel = path.relative_to(root)
            if any(part in EXCLUDES for part in rel.parts):
                continue
            if path.is_file() and not path.name.endswith((".pyc", ".db", ".sqlite", ".xlsx", ".csv", ".part")):
                zf.write(path, rel)
    digest = sha256(archive)
    (archive.with_suffix(archive.suffix + ".sha256")).write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Release package created: {archive}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
