import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
c=conn.cursor()

before = c.execute(
    "SELECT COUNT(*) FROM stop_routes"
).fetchone()[0]


# backup invalid rows
c.execute("""
DROP TABLE IF EXISTS stop_routes_invalid_key_backup
""")

c.execute("""
CREATE TABLE stop_routes_invalid_key_backup AS

SELECT sr.*

FROM stop_routes sr

LEFT JOIN routes r
    ON r.id = sr.route_id

WHERE r.id IS NULL
""")


invalid = c.execute("""
SELECT COUNT(*)
FROM stop_routes_invalid_key_backup
""").fetchone()[0]


print("Invalid rows found:", invalid)


# remove invalid rows
c.execute("""
DELETE FROM stop_routes

WHERE id IN (
    SELECT id
    FROM stop_routes_invalid_key_backup
)
""")


removed = c.rowcount

print("Removed:", removed)


# restore through route code lookup

c.execute("""
INSERT OR IGNORE INTO stop_routes
(
    stop_id,
    route_id
)

SELECT DISTINCT

    b.stop_id,
    r.id

FROM stop_routes_invalid_key_backup b

JOIN routes r

    ON r.route_id = b.route_id
""")


conn.commit()


after = c.execute(
    "SELECT COUNT(*) FROM stop_routes"
).fetchone()[0]


print("Before:", before)
print("After:", after)
print("Net change:", after-before)


conn.close()