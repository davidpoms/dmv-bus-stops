import sqlite3
import shutil
from datetime import datetime

DB = "src/database/dmv_bus_stops.db"

backup = f"{DB}.before_route_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

shutil.copy(DB, backup)

print("Database backup created:")
print(backup)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Preview count
count = c.execute("""
SELECT COUNT(*)
FROM stop_routes_bad_key_backup b
JOIN routes r
ON (
    r.route_id = CAST(b.route_id AS TEXT)
    OR r.id = b.route_id
)
LEFT JOIN stop_routes sr
ON sr.stop_id = b.stop_id
AND sr.route_id = r.id
WHERE sr.id IS NULL
""").fetchone()[0]

print()
print("Rows to restore:", count)

confirm = input("Continue? (yes/no): ")

if confirm.lower() != "yes":
    print("Cancelled")
    conn.close()
    exit()

c.execute("BEGIN")

c.execute("""
INSERT INTO stop_routes(stop_id, route_id)
SELECT
    b.stop_id,
    r.id
FROM stop_routes_bad_key_backup b
JOIN routes r
ON (
    r.route_id = CAST(b.route_id AS TEXT)
    OR r.id = b.route_id
)
LEFT JOIN stop_routes sr
ON sr.stop_id = b.stop_id
AND sr.route_id = r.id
WHERE sr.id IS NULL
""")

inserted = c.rowcount

conn.commit()

print()
print("Inserted:", inserted)

# Verification
remaining = c.execute("""
SELECT COUNT(*)
FROM physical_stops p
LEFT JOIN physical_stop_members psm
ON p.id = psm.physical_stop_id
LEFT JOIN stop_routes sr
ON psm.bus_stop_id = sr.stop_id
WHERE sr.id IS NULL
""").fetchone()[0]

print("Physical stops still without routes:", remaining)

conn.close()