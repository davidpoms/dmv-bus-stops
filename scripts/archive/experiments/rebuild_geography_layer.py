import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("Creating stop_jurisdiction...")

cur.execute("""
DROP TABLE IF EXISTS stop_jurisdiction
""")

cur.execute("""
CREATE TABLE stop_jurisdiction (
    stop_id INTEGER PRIMARY KEY,
    state TEXT,
    dc_ward TEXT,
    dc_anc TEXT,
    county TEXT,
    municipality TEXT
)
""")

cur.execute("""
INSERT INTO stop_jurisdiction
(
    stop_id,
    state,
    dc_ward,
    dc_anc,
    county,
    municipality
)
SELECT
    id,
    state,
    dc_ward,
    dc_anc,
    county,
    municipality
FROM physical_stops
""")

print("Creating summary tables...")

for table in [
    "dc_ward_summary",
    "dc_anc_summary",
    "county_summary",
    "municipality_summary"
]:
    cur.execute(f"DROP TABLE IF EXISTS {table}")


cur.execute("""
CREATE TABLE dc_ward_summary AS
SELECT
    dc_ward AS ward,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE dc_ward IS NOT NULL
GROUP BY dc_ward
""")


cur.execute("""
CREATE TABLE dc_anc_summary AS
SELECT
    dc_anc AS anc,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE dc_anc IS NOT NULL
GROUP BY dc_anc
""")


cur.execute("""
CREATE TABLE county_summary AS
SELECT
    state,
    county,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE county IS NOT NULL
GROUP BY state, county
""")


cur.execute("""
CREATE TABLE municipality_summary AS
SELECT
    state,
    county,
    municipality,
    COUNT(*) AS stop_count
FROM stop_jurisdiction
WHERE municipality IS NOT NULL
GROUP BY state, county, municipality
""")


conn.commit()


print("Validation:")

for table in [
    "stop_jurisdiction",
    "dc_ward_summary",
    "dc_anc_summary",
    "county_summary",
    "municipality_summary"
]:
    count = cur.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(table, count)


conn.close()

print("Geography layer rebuilt")