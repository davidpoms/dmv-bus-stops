import sqlite3
from datetime import datetime

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()


c.execute("""
CREATE TABLE IF NOT EXISTS gtfs_orphan_route_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gtfs_stop_id TEXT,
    route_id TEXT,
    reason TEXT,
    created_at TEXT
)
""")


c.execute("DELETE FROM gtfs_orphan_route_audit")


c.execute("""
INSERT INTO gtfs_orphan_route_audit
(
    gtfs_stop_id,
    route_id,
    reason,
    created_at
)

SELECT
    CAST(srb.stop_id AS TEXT),
    srb.route_id,
    'GTFS stop exists in historical route feed but no current bus_stop mapping',
    ?

FROM stop_routes_backup srb

LEFT JOIN gtfs_stop_map gm
    ON CAST(srb.stop_id AS TEXT)=gm.gtfs_stop_id

WHERE gm.gtfs_stop_id IS NULL

GROUP BY
    srb.stop_id,
    srb.route_id
""", (datetime.now().isoformat(),))


conn.commit()


print(
    "Audit rows:",
    c.execute(
        "SELECT COUNT(*) FROM gtfs_orphan_route_audit"
    ).fetchone()[0]
)


conn.close()

print("Done.")