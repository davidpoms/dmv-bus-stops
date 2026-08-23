import sqlite3
import json


DB = "src/database/dmv_bus_stops.db"

stop_id = 5513

conn = sqlite3.connect(DB)

conn.row_factory = sqlite3.Row

c = conn.cursor()


print("\n=== improvement_opportunities ===")

row = c.execute(
    """
    SELECT *
    FROM improvement_opportunities
    WHERE physical_stop_id=?
    """,
    (stop_id,)
).fetchone()

print(dict(row) if row else None)


print("\n=== stop_improvement_impact ===")

row = c.execute(
    """
    SELECT *
    FROM stop_improvement_impact
    WHERE physical_stop_id=?
    """,
    (stop_id,)
).fetchone()

print(dict(row) if row else None)


print("\n=== live ridership ===")

row = c.execute(
    """
    SELECT
        SUM(rs.weekday_boardings),
        COUNT(DISTINCT r.route_id),
        GROUP_CONCAT(DISTINCT r.route_id)

    FROM physical_stop_members psm

    JOIN stop_routes sr
    ON psm.bus_stop_id = sr.stop_id

    JOIN routes r
    ON sr.route_id=r.id

    JOIN ridership_snapshots rs
    ON r.route_id=rs.route_id

    WHERE psm.physical_stop_id=?

    AND rs.period=(
        SELECT MAX(period)
        FROM ridership_snapshots
    )
    """,
    (stop_id,)
).fetchone()

print(dict(row))


conn.close()