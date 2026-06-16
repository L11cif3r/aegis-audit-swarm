"""Verify the live database schema matches the models.

Runs the same create/sync logic the app runs at startup, then reports every
table and any columns that are still missing. Safe + idempotent.

    cd backend && source venv/bin/activate && python scripts/verify_db.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy  # noqa: E402

from database import metadata, create_tables, _sync_engine  # noqa: E402


def main() -> int:
    print("Applying create_tables() + column sync …")
    create_tables()

    engine = _sync_engine()
    insp = sqlalchemy.inspect(engine)
    db_tables = set(insp.get_table_names())

    print("\n=== Schema verification ===")
    ok = True
    for table in metadata.sorted_tables:
        if table.name not in db_tables:
            print(f"[FAIL] {table.name}: TABLE MISSING")
            ok = False
            continue
        db_cols = {c["name"] for c in insp.get_columns(table.name)}
        model_cols = {c.name for c in table.columns}
        missing = model_cols - db_cols
        if missing:
            print(f"[FAIL] {table.name}: {len(db_cols)} cols — MISSING {sorted(missing)}")
            ok = False
        else:
            print(f"[ OK ] {table.name}: {len(db_cols)} cols")

    extra = sorted(db_tables - {t.name for t in metadata.sorted_tables})
    if extra:
        print(f"\nOther tables in DB (not modeled by backend): {extra}")

    print("\n" + ("ALL GOOD — schema in sync." if ok else "ISSUES FOUND — see above."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
