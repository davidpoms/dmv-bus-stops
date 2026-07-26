from pathlib import Path

path = Path("src/assessment/generate_improvement_recommendations.py")

text = path.read_text()


# Remove the accidental Python block inserted into SQL
bad_block = """
    transit = conn.execute(
        '''
        SELECT
            gtfs_bus_stop
        FROM stop_transit_evidence
        WHERE stop_id=?
        ''',
        (stop_id,)
    ).fetchone()

    gtfs_bus_stop = (
        transit["gtfs_bus_stop"]
        if transit
        else 0
    )

"""

if bad_block in text:
    text = text.replace(bad_block, "")
else:
    print("Bad block not found; continuing")


# Fix SELECT statement to include transit evidence
old = """
            COALESCE(ose.osm_shelter,0)


        FROM improvement_opportunities io

        LEFT JOIN stop_osm_evidence ose

            ON ose.stop_id = io.physical_stop_id
"""

new = """
            COALESCE(ose.osm_shelter,0),

            COALESCE(ste.gtfs_bus_stop,0)


        FROM improvement_opportunities io

        LEFT JOIN stop_osm_evidence ose

            ON ose.stop_id = io.physical_stop_id

        LEFT JOIN stop_transit_evidence ste

            ON ste.stop_id = io.physical_stop_id
"""

if old not in text:
    raise Exception("SELECT block not found")

text = text.replace(old, new)


# Add row unpacking
old = """
            osm_bench,
            osm_shelter
        ) = row
"""

new = """
            osm_bench,
            osm_shelter,
            gtfs_bus_stop
        ) = row
"""

if old not in text:
    raise Exception("row unpack block not found")

text = text.replace(old, new)


# Add GTFS into evidence dictionaries
old = """
            "osm_shelter": osm_shelter
"""

new = """
            "osm_shelter": osm_shelter,
            "gtfs_bus_stop": gtfs_bus_stop
"""

text = text.replace(old, new)


# Improve reasons
text = text.replace(
    '"No bench mapped in OSM"',
    '"No bench mapped at active transit stop" if gtfs_bus_stop else "No bench mapped in OSM"'
)

text = text.replace(
    '"No shelter mapped in OSM"',
    '"No shelter mapped at active transit stop" if gtfs_bus_stop else "No shelter mapped in OSM"'
)


path.write_text(text)

print("Fixed recommendation generator transit integration.")
