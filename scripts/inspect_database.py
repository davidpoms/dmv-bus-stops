import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("\nDATABASE:")
print(DB)
print("Size:", DB.stat().st_size, "bytes")


print("\nTABLES")
print("=" * 40)

tables = [
    r[0]
    for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
]

for table in tables:
    count = cur.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"\n{table} ({count} rows)")

    columns = cur.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    for col in columns:
        print(f"  - {col[1]} ({col[2]})")


print("\nVIEWS")
print("=" * 40)

views = [
    r[0]
    for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    )
]

for view in views:
    print("-", view)


conn.close()