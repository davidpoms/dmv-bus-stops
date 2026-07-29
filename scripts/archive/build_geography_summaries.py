import sqlite3
from pathlib import Path

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)

queries = {

"jurisdiction_summary": """
CREATE TABLE IF NOT EXISTS jurisdiction_summary AS
SELECT
    state,
    county,
    municipality,
    municipality_type,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
GROUP BY
    state,
    county,
    municipality,
    municipality_type;
""",

"dc_ward_summary": """
CREATE TABLE IF NOT EXISTS dc_ward_summary AS
SELECT
    dc_ward,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE state='DC'
GROUP BY dc_ward;
""",

"dc_anc_summary": """
CREATE TABLE IF NOT EXISTS dc_anc_summary AS
SELECT
    dc_anc,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE state='DC'
GROUP BY dc_anc;
"""
}


for name,q in queries.items():

    print("Building", name)

    conn.execute(
        "DROP TABLE IF EXISTS " + name
    )

    conn.execute(q)


conn.commit()
conn.close()

print("Finished")
