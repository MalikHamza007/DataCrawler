from __future__ import annotations

from app.commands._ops import alembic_current, alembic_head, quick_check


def main() -> int:
    try:
        if alembic_current() != alembic_head():
            print("unhealthy: schema is not current")
            return 1
        if quick_check() != "ok":
            print("unhealthy: database quick_check failed")
            return 1
    except Exception as exc:
        print(f"unhealthy: {exc}")
        return 1
    print("healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
