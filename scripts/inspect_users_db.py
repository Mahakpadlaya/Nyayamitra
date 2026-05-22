"""Print users from legal_advisor.db (project root and backend/ if present)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in [ROOT / "legal_advisor.db", ROOT / "backend" / "legal_advisor.db"]:
    print(f"\n--- {p}")
    if not p.exists():
        print("  (file missing)")
        continue
    con = sqlite3.connect(p)
    tables = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    print("  tables:", [t[0] for t in tables])
    try:
        rows = con.execute(
            "SELECT id, email, first_name, last_name, created_at FROM users"
        ).fetchall()
        print(f"  users ({len(rows)} rows):")
        for row in rows:
            print("   ", row)
    except sqlite3.OperationalError as e:
        print("  users:", e)
    con.close()
