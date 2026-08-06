import requests
import sqlite3


DB = "src/database/dmv_bus_stops.db"

URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)


params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "false",
    "f": "json"
}


data = requests.get(URL, params=params).json()

records = data["features"]

print("DDOT records:", len(records))


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


matched = 0
physical = 0
missing = []


for feature in records:

    a = feature["attributes"]

    ddot_id = str(
        a.get("DDOT_SHELTER_ID")
    )

    if not ddot_id or ddot_id == "None":
        continue


    row = conn.execute(
        """
        SELECT
            b.id,
            b.external_stop_id,
            ps.id AS physical_stop_id

        FROM bus_stops b

        LEFT JOIN physical_stop_members psm
        ON psm.bus_stop_id=b.id

        LEFT JOIN physical_stops ps
        ON ps.id=psm.physical_stop_id

        WHERE b.external_stop_id=?
        """,
        (ddot_id,)
    ).fetchone()


    if row:

        matched += 1

        if row["physical_stop_id"]:
            physical += 1

    else:
        missing.append(ddot_id)


print("GTFS matched:", matched)
print("Physical matched:", physical)
print("Missing:", len(missing))

print("First missing:")
print(missing[:25])


conn.close()