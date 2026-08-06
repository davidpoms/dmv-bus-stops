import sqlite3


conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

conn.row_factory = sqlite3.Row


for r in conn.execute("""
SELECT
    external_stop_id,
    stop_name,
    latitude,
    longitude
FROM bus_stops
WHERE external_stop_id LIKE '1%'
LIMIT 25
"""):

    print(dict(r))


conn.close()