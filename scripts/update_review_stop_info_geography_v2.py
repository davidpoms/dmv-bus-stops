from pathlib import Path
import re

p = Path("src/api/app.py")

text = p.read_text()


pattern = r'(@app\.route\("/review/<int:stop_id>/info"\)\ndef .*?\n)(.*?)(?=\n\n@app\.route|\Z)'


match = re.search(pattern, text, re.S)

if not match:
    raise Exception(
        "Could not find review stop info route"
    )


new_function = r'''@app.route("/review/<int:stop_id>/info")
def review_stop_info(stop_id):

    stop = query_db(
        """
        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            state,
            dc_ward,
            dc_anc,
            county,
            municipality

        FROM physical_stops

        WHERE id = ?;
        """,
        (stop_id,)
    )


    if not stop:
        return "Stop not found", 404


    row = stop[0]


    if row[4] == "DC":

        jurisdiction = "Washington, DC"

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

        jurisdiction = row[4] or "Unknown"

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
            "jurisdiction": jurisdiction,
            "geography": geography,
            "streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
        }
    )
'''


text = text[:match.start()] + new_function + text[match.end():]


p.write_text(text)

print("Updated review stop info geography route")
