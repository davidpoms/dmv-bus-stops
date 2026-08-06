import requests
import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)

conn.row_factory = sqlite3.Row


matched_ids = {
    r["source_record_id"]
    for r in conn.execute(
        """
        SELECT source_record_id
        FROM stop_amenity_evidence
        WHERE source='DDOT'
        """
    )
}


conn.close()


url = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)


params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "false",
    "f": "json"
}


data = requests.get(
    url,
    params=params
).json()


features = data["features"]


print(
    "DDOT records:",
    len(features)
)

print(
    "Existing matched records:",
    len(matched_ids)
)


count = 0


for feature in features:

    a = feature["attributes"]

    shelter_id = str(
        a.get("DDOT_SHELTER_ID")
    )


    if shelter_id not in matched_ids:

        print(
            {
                "DDOT_SHELTER_ID": shelter_id,
                "DDOT_ID": a.get("DDOT_ID"),
                "Site_Code": a.get("Site_Code"),
                "Barcode": a.get("Barcode"),
                "Address": a.get("Sales_Address"),
                "Zip": a.get("Zip")
            }
        )

        count += 1


        if count >= 20:
            break


print(
    "Displayed:",
    count
)