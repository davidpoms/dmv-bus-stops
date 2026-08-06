import sqlite3


conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

for r in conn.execute("""
SELECT
    substr(external_stop_id,1,1) AS prefix,
    COUNT(*) AS count
FROM bus_stops
GROUP BY prefix
ORDER BY prefix
"""):
    print(r)


conn.close()