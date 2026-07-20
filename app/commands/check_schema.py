from __future__ import annotations

from app.commands._ops import alembic_current, alembic_head


def main() -> int:
    current = alembic_current()
    head = alembic_head()
    if current == head:
        print("Database schema is current.")
        return 0
    print(f"Database revision {current} is behind expected revision {head}. Run migrations before starting the application.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
