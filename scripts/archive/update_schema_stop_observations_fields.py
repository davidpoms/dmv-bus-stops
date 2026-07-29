from pathlib import Path


schema_path = Path("src/database/schema.sql")

text = schema_path.read_text()


old = """    streetview_checked BOOLEAN,

    osm_checked BOOLEAN,

    FOREIGN KEY(physical_stop_id)
        REFERENCES physical_stops(id)
"""


new = """    streetview_checked BOOLEAN,

    osm_checked BOOLEAN,

    review_mode TEXT,

    rider_activity TEXT,

    usage_times TEXT,

    property_owner_outreach TEXT,

    steward_email TEXT,

    steward_candidate BOOLEAN DEFAULT 0,

    FOREIGN KEY(physical_stop_id)
        REFERENCES physical_stops(id)
"""


if "review_mode TEXT" in text:
    print("Schema already updated. No changes made.")
    raise SystemExit(0)


if old not in text:
    raise SystemExit(
        "Could not find expected stop_observations schema section."
    )


text = text.replace(old, new)


schema_path.write_text(text)


print("Updated schema.sql with new stop_observations fields.")
