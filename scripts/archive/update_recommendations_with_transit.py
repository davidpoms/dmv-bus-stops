from pathlib import Path

path = Path("src/assessment/generate_improvement_recommendations.py")

text = path.read_text()


# Add transit lookup after OSM evidence lookup if not already present
if "stop_transit_evidence" not in text:

    marker = "osm_shelter"

    idx = text.find(marker)

    if idx == -1:
        raise Exception("Could not find OSM evidence section")

    insert_point = text.find("\n", idx)

    addition = """

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

    text = text[:insert_point+1] + addition + text[insert_point+1:]


# Add gtfs field to evidence dictionaries
old = '''"osm_shelter": osm_shelter
'''

new = '''"osm_shelter": osm_shelter,
        "gtfs_bus_stop": gtfs_bus_stop
'''

if old in text:
    text = text.replace(old, new)


# Replace generic wording
text = text.replace(
    '"No bench mapped in OSM"',
    '("No bench mapped at active transit stop" if gtfs_bus_stop == 1 else "No bench mapped in OSM")'
)

text = text.replace(
    '"No shelter mapped in OSM"',
    '("No shelter mapped at active transit stop" if gtfs_bus_stop == 1 else "No shelter mapped in OSM")'
)


path.write_text(text)

print("Updated recommendation generator with transit evidence.")
