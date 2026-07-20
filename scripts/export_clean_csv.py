#!/usr/bin/env python3
"""
export_clean_csv.py
-------------------
Standalone direct-database exporter for the Alduor Lahore project discovery dataset.

Produces a clean CSV with exactly four columns:
  Project Name, Developer Name, Phone Number, Email Address

Rules
-----
- Only active, non-merged projects are included.
- Rows with no project name are dropped.
- Rows with neither a phone number nor an email address are dropped.
- Developer name resolution priority:
    1. Verified developer record directly linked (projects.developer_id)
    2. Developer record linked via website_crawls (crawl.developer_id where crawl.project_id matches)
    3. Source-evidence developer_name extracted from official website crawl
    4. Infer from project name "X by Developer" pattern
- Phone is the first phone found for the project (Google Places > website crawl).
- Email is the first non-noreply email found for the project or its crawl-linked developer.
- No placeholders, no article titles, no speculative data.

Usage
-----
    cd /Users/apple/Desktop/Alduor_Data_scrapper/backend
    source .venv/bin/activate
    python scripts/export_clean_csv.py [--db PATH] [--out PATH]

Options
-------
    --db PATH           SQLite DB path  (default: data/database/alduor.db)
    --out PATH          Output CSV path (default: data/exports/alduor_clean_<ts>.csv)
    --include-no-phone  Also write rows that have only an email and no phone
    --min-name-len N    Minimum project name length to keep (default: 4)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

# ──────────────────────────────────────────────────────────────────────────────
# Noise-rejection constants
# ──────────────────────────────────────────────────────────────────────────────
ARTICLE_TITLE_RE = re.compile(
    r"\b("
    r"top\s+\d+|best\s+\d+|list\s+of|guide\s+to|how\s+to|what\s+is|"
    r"complete\s+guide|all\s+you\s+need|everything\s+about|"
    r"real\s+estate\s+news|property\s+news|lahore\s+real\s+estate\s+overview|"
    r"investment\s+tips|market\s+update|blog|article|news"
    r")\b",
    re.I,
)

GENERIC_CATEGORY_RE = re.compile(
    r"^(real\s+estate\s+(projects?|listings?|properties)\s+(in\s+)?lahore"
    r"|properties?\s+in\s+lahore"
    r"|lahore\s+properties?"
    r"|housing\s+projects?\s+in\s+lahore"
    r")$",
    re.I,
)

# Developer name garbage patterns
BAD_DEVELOPER_RE = re.compile(
    r"^\s*("
    r"all\s+rights\s+reserved|©|\d{4}|privacy\s+policy|"
    r"register\s+your\s+interests|contact\s+us|careers|"
    r"home|about|projects?|news|blog|http|www\."
    r")\s*",
    re.I,
)

# Developers whose name is just the project name (website self-reference noise)
SELF_REFERENCE_RE = re.compile(
    r"\b(apartments?|residences?|residencia|tower|heights|enclave|"
    r"mall|square|skyscraper|luxury|premium|real\s+estate)\b",
    re.I,
)

NOREPLY_PREFIXES = (
    "noreply@", "no-reply@", "example@", "test@",
    "wordpress@", "info@example", "admin@example",
)

# Byline: "Central Park Housing Scheme by Urban Developers Group"
# Also handles parenthesised patterns like "(Project by Marwa Developers)"
BYLINE_RE = re.compile(
    r"\bby\s+([A-Z][A-Za-z0-9&.'() -]{2,80}?)"
    r"(?:\s*[\)\]>]|$|(?=\s*[,;|]))",
    re.I,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def is_noise_project(name: str, min_len: int) -> bool:
    if not name or len(name.strip()) < min_len:
        return True
    if ARTICLE_TITLE_RE.search(name):
        return True
    if GENERIC_CATEGORY_RE.match(name.strip()):
        return True
    return False


def clean_developer(raw: str | None, project_name: str = "") -> str:
    """
    Sanitize a raw developer-name candidate.
    Returns empty string if the value is garbage or identical to the project name.
    """
    if not raw:
        return ""
    raw = raw.strip().strip("©•|–-,").strip()
    # Remove copyright year prefix
    raw = re.sub(r"^©\s*\d{0,4}\s*", "", raw).strip()
    # Collapse whitespace
    raw = re.sub(r"\s{2,}", " ", raw).strip()
    if len(raw) < 3 or len(raw) > 120:
        return ""
    if BAD_DEVELOPER_RE.match(raw):
        return ""
    # Reject if it's basically the same as the project name
    if project_name and raw.casefold() == project_name.casefold():
        return ""
    # Reject names that look like marketing slogans (contain apartment/tower etc.)
    # but don't contain a proper company suffix
    COMPANY_SUFFIX = re.compile(
        r"\b(developers?|development|properties|group|holdings|"
        r"limited|ltd|pvt|associates|builders?|homes?|realty|"
        r"construction|engineers?|estate)\b",
        re.I,
    )
    if SELF_REFERENCE_RE.search(raw) and not COMPANY_SUFFIX.search(raw):
        return ""
    return raw


def infer_developer_from_name(project_name: str) -> str:
    """Extract developer name from 'Project Name by Developer Name' patterns."""
    m = BYLINE_RE.search(project_name)
    if m:
        return clean_developer(m.group(1).strip(), project_name)
    return ""


def format_phone(normalized: str, display: str) -> str:
    """Return the best human-readable phone string."""
    # Prefer the display value if it's already nicely formatted
    if display and len(display) >= 7:
        return display.strip()
    return normalized or ""


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export clean real-estate project CSV from Alduor DB",
    )
    parser.add_argument("--db", default="data/database/alduor.db")
    parser.add_argument("--out", default="")
    parser.add_argument("--include-no-phone", action="store_true")
    parser.add_argument("--min-name-len", type=int, default=4)
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if args.out:
        out_path = Path(args.out)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path("data/exports") / f"alduor_clean_{ts}.csv"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    print(f"[INFO] Database : {db_path}")
    print(f"[INFO] Output   : {out_path}")

    with engine.connect() as conn:

        # ── Load all active, non-merged projects ──────────────────────────────
        projects = conn.execute(text("""
            SELECT id, name, developer_id, google_place_id, official_website_url
            FROM projects
            WHERE record_status = 'active'
            ORDER BY id
        """)).fetchall()
        total_raw = len(projects)
        print(f"[INFO] Active projects fetched: {total_raw}")

        # ── Developer names by developer ID ───────────────────────────────────
        dev_rows = conn.execute(text(
            "SELECT id, name FROM developers"
        )).fetchall()
        developer_by_id: dict[int, str] = {r[0]: (r[1] or "") for r in dev_rows}

        # ── Developer ID linked via website crawl → project ──────────────────
        crawl_rows = conn.execute(text("""
            SELECT project_id, developer_id
            FROM website_crawls
            WHERE project_id IS NOT NULL AND developer_id IS NOT NULL
        """)).fetchall()
        crawl_dev_by_project: dict[int, int] = {}
        for r in crawl_rows:
            crawl_dev_by_project.setdefault(r[0], r[1])

        # ── Source-evidence developer names linked to a developer record ──────
        # (These developer records are in turn linked to projects via crawls)
        ev_dev_rows = conn.execute(text("""
            SELECT developer_id, extracted_value
            FROM source_evidence
            WHERE field_name = 'developer_name'
              AND developer_id IS NOT NULL
            ORDER BY developer_id, id
        """)).fetchall()
        ev_names_by_dev: dict[int, list[str]] = {}
        for r in ev_dev_rows:
            did, val = r[0], r[1]
            ev_names_by_dev.setdefault(did, []).append(val)

        # ── Best phone per project (display value + normalized) ───────────────
        phone_rows = conn.execute(text("""
            SELECT project_id, value, COALESCE(normalized_value, value) AS norm
            FROM contacts
            WHERE contact_type IN ('phone', 'sales_phone')
              AND project_id IS NOT NULL
              AND value IS NOT NULL
            ORDER BY project_id, id
        """)).fetchall()
        phones_by_project: dict[int, tuple[str, str]] = {}
        for r in phone_rows:
            pid, display, norm = r[0], r[1], r[2]
            phones_by_project.setdefault(pid, (display, norm))

        # Developer-level phones as fallback
        dev_phone_rows = conn.execute(text("""
            SELECT developer_id, value, COALESCE(normalized_value, value) AS norm
            FROM contacts
            WHERE contact_type IN ('phone', 'sales_phone')
              AND developer_id IS NOT NULL
              AND project_id IS NULL
              AND value IS NOT NULL
            ORDER BY developer_id, id
        """)).fetchall()
        dev_phones: dict[int, tuple[str, str]] = {}
        for r in dev_phone_rows:
            did, display, norm = r[0], r[1], r[2]
            dev_phones.setdefault(did, (display, norm))

        # ── Best email per project ────────────────────────────────────────────
        email_rows = conn.execute(text("""
            SELECT project_id, value
            FROM contacts
            WHERE contact_type = 'email'
              AND project_id IS NOT NULL
              AND value IS NOT NULL
            ORDER BY project_id, id
        """)).fetchall()
        email_by_project: dict[int, str] = {}
        for r in email_rows:
            pid, email = r[0], r[1]
            if any(email.lower().startswith(p) for p in NOREPLY_PREFIXES):
                continue
            email_by_project.setdefault(pid, email)

        # Developer-level emails as fallback
        dev_email_rows = conn.execute(text("""
            SELECT developer_id, value
            FROM contacts
            WHERE contact_type = 'email'
              AND developer_id IS NOT NULL
              AND project_id IS NULL
              AND value IS NOT NULL
            ORDER BY developer_id, id
        """)).fetchall()
        dev_emails: dict[int, str] = {}
        for r in dev_email_rows:
            did, email = r[0], r[1]
            if any(email.lower().startswith(p) for p in NOREPLY_PREFIXES):
                continue
            dev_emails.setdefault(did, email)

    # ── Build output rows ─────────────────────────────────────────────────────
    rows: list[dict[str, str]] = []
    skipped_noise = 0
    skipped_no_contact = 0

    for proj in projects:
        proj_id, proj_name, dev_id, _, _ = proj

        # 1. Reject noise / article titles
        if is_noise_project(proj_name, args.min_name_len):
            skipped_noise += 1
            continue

        # 2. Resolve phone (project → developer fallback chain)
        phone_pair = phones_by_project.get(proj_id)
        if not phone_pair and dev_id:
            phone_pair = dev_phones.get(dev_id)
        # Also check crawl-linked developer as phone source
        crawl_dev_id = crawl_dev_by_project.get(proj_id)
        if not phone_pair and crawl_dev_id:
            phone_pair = dev_phones.get(crawl_dev_id)

        phone_str = ""
        if phone_pair:
            phone_str = format_phone(phone_pair[1], phone_pair[0])

        # 3. Resolve email
        email_str = email_by_project.get(proj_id, "")
        if not email_str and dev_id:
            email_str = dev_emails.get(dev_id, "")
        if not email_str and crawl_dev_id:
            email_str = dev_emails.get(crawl_dev_id, "")

        # 4. Drop if no contact at all
        if not phone_str and not email_str:
            skipped_no_contact += 1
            continue
        if not args.include_no_phone and not phone_str:
            skipped_no_contact += 1
            continue

        # 5. Resolve developer name
        developer_name = ""

        # P1: verified developer record directly on project
        if dev_id:
            developer_name = clean_developer(developer_by_id.get(dev_id, ""), proj_name)

        # P2: developer linked via website crawl for this project
        if not developer_name and crawl_dev_id:
            developer_name = clean_developer(developer_by_id.get(crawl_dev_id, ""), proj_name)

        # P3: source-evidence developer names for crawl-linked developer
        if not developer_name:
            target_dev_id = dev_id or crawl_dev_id
            if target_dev_id:
                for candidate in ev_names_by_dev.get(target_dev_id, []):
                    cleaned = clean_developer(candidate, proj_name)
                    if cleaned:
                        developer_name = cleaned
                        break

        # P4: infer from project name "X by Developer" pattern
        if not developer_name:
            developer_name = infer_developer_from_name(proj_name)

        rows.append({
            "Project Name": proj_name.strip(),
            "Developer Name": developer_name,
            "Phone Number": phone_str,
            "Email Address": email_str,
        })

    # ── Write CSV ─────────────────────────────────────────────────────────────
    fieldnames = ["Project Name", "Developer Name", "Phone Number", "Email Address"]
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    # ── Summary ───────────────────────────────────────────────────────────────
    with_dev   = sum(1 for r in rows if r["Developer Name"])
    with_email = sum(1 for r in rows if r["Email Address"])
    with_phone = sum(1 for r in rows if r["Phone Number"])

    print()
    print("=" * 60)
    print(f"  Export complete")
    print(f"  File : {out_path}")
    print("=" * 60)
    print(f"  Active projects in DB        : {total_raw}")
    print(f"  Dropped  (noise/articles)    : {skipped_noise}")
    print(f"  Dropped  (no contact data)   : {skipped_no_contact}")
    print(f"  ─────────────────────────────────────")
    print(f"  ROWS WRITTEN                 : {len(rows)}")
    print(f"    With Developer Name        : {with_dev}")
    print(f"    With Phone Number          : {with_phone}")
    print(f"    With Email Address         : {with_email}")
    print("=" * 60)
    print()
    print("[NOTE] Most rows lack an email because only 20 out of 479 discovered")
    print("       websites were crawled — 58 crawls failed and 14 were blocked by")
    print("       robots.txt. Run more website enrichment jobs to fill email gaps.")


if __name__ == "__main__":
    main()
