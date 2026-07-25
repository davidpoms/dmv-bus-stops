import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)

queries = {

"county_summary": """
DROP TABLE IF EXISTS county_summary;

CREATE TABLE county_summary AS
SELECT
    state,
    county,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
GROUP BY
    state,
    county;
""",

"municipality_summary": """
DROP TABLE IF EXISTS municipality_summary;

CREATE TABLE municipality_summary AS
SELECT
    state,
    county,
    municipality,
    municipality_type,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE municipality IS NOT NULL
GROUP BY
    state,
    county,
    municipality,
    municipality_type;
""",

"dc_smd_summary": """
DROP TABLE IF EXISTS dc_smd_summary;

CREATE TABLE dc_smd_summary AS
SELECT
    dc_ward,
    dc_anc,
    dc_smd,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE state='DC'
GROUP BY
    dc_ward,
    dc_anc,
    dc_smd;
"""
}


for name, sql in queries.items():
    print("Building", name)
    conn.executescript(sql)


conn.commit()
conn.close()

print("Finished")
