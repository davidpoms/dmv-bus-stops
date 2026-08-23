import requests
import sqlite3


DB="src/database/dmv_bus_stops.db"

URL=(
"https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
"Planning/FeatureServer/1/query"
)


params={
    "where":"1=1",
    "outFields":"DDOT_SHELTER_ID",
    "returnGeometry":"false",
    "f":"json"
}


data=requests.get(URL,params=params).json()

records=data["features"]

conn=sqlite3.connect(DB)

gtfs=0
physical=0
missing=[]

for feature in records:

    attrs=feature["attributes"]

    ddot=str(
        attrs.get("DDOT_SHELTER_ID")
    )

    row=conn.execute(
        """
        SELECT id
        FROM bus_stops
        WHERE external_stop_id=?
        """,
        (ddot,)
    ).fetchone()

    if row:
        gtfs+=1

        p=conn.execute(
            """
            SELECT physical_stop_id
            FROM physical_stop_members
            WHERE bus_stop_id=?
            """,
            (row[0],)
        ).fetchone()

        if p:
            physical+=1
    else:
        missing.append(ddot)


print("DDOT:",len(records))
print("GTFS matches:",gtfs)
print("Physical matches:",physical)
print("Missing GTFS:",len(missing))

print(missing[:20])

conn.close()