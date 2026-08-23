import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

for row in conn.execute("""
SELECT
    state,
    county,
    municipality,
    COUNT(*)
FROM stop_jurisdiction
GROUP BY state, county, municipality
ORDER BY COUNT(*) DESC
LIMIT 30
"""):
    print(row)

conn.close()