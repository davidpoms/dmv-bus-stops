import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

checks = {
    "Active GTFS evidence":
    """
    SELECT COUNT(*)
    FROM stop_transit_evidence
    WHERE gtfs_bus_stop=1
    """,

    "Physical stops with GTFS evidence":
    """
    SELECT COUNT(DISTINCT ps.id)
    FROM physical_stops ps
    JOIN stop_transit_evidence ste
        ON ps.id = ste.stop_id
    WHERE ste.gtfs_bus_stop=1
    """,

    "Physical stops with opportunities":
    """
    SELECT COUNT(DISTINCT ps.id)
    FROM physical_stops ps
    JOIN improvement_opportunities io
        ON ps.id = io.physical_stop_id
    JOIN stop_transit_evidence ste
        ON ps.id = ste.stop_id
    WHERE ste.gtfs_bus_stop=1
    """
}

for name, query in checks.items():
    print(name, ":", c.execute(query).fetchone()[0])

conn.close()