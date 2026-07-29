from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        SELECT
            ps.id,
            ps.primary_name,
            ps.latitude,
            ps.longitude,
            ps.jurisdiction

        FROM physical_stops ps

        WHERE ps.id = ?;
"""

new = """
        SELECT
            ps.id,
            ps.primary_name,
            ps.latitude,
            ps.longitude,
            ps.state,
            ps.dc_ward,
            ps.dc_anc,
            ps.county,
            ps.municipality

        FROM physical_stops ps

        WHERE ps.id = ?;
"""

if old not in text:
    raise Exception("Could not find old stop info query")

text = text.replace(old, new)


old_return = """
    row = stop[0]

    return jsonify(
        {
            "stop_id": row[0],
            "location": row[1],
            "lat": row[2],
            "lon": row[3],
            "streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
        }
    )
"""

new_return = """
    row = stop[0]

    state = row[4]

    if state == "DC":

        location = (
            "Washington, DC"
        )

        geography = []

        if row[5]:
            geography.append(
                f"Ward {int(row[5])}"
            )

        if row[6]:
            geography.append(
                f"ANC {row[6]}"
            )

    else:

        location = state or "Unknown"

        geography = []

        if row[7]:
            geography.append(
                row[7]
            )

        if row[8]:
            geography.append(
                row[8]
            )


    return jsonify(
        {
            "stop_id": row[0],
            "location": row[1],
            "lat": row[2],
            "lon": row[3],
            "jurisdiction": location,
            "geography": geography,
            "streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
        }
    )
"""

if old_return not in text:
    raise Exception("Could not find old return block")

text = text.replace(old_return, new_return)

p.write_text(text)

print("Updated review stop geography endpoint")
