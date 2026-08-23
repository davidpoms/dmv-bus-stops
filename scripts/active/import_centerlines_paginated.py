import sqlite3
import requests
import json
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")


SOURCES = [

("fairfax",
"https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/OpenData_A1/FeatureServer/0/query"),

("dc",
"https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Transportation_WebMercator/MapServer/163/query"),

("montgomery",
"https://gis3.montgomerycountymd.gov/arcgis/rest/services/GDX/street_centerline/FeatureServer/0/query")

]


conn = sqlite3.connect(DB)


for source,url in SOURCES:

    offset = 0
    total = 0

    print("\nDownloading", source)

    while True:

        params = {
            "where":"1=1",
            "outFields":"*",
            "f":"geojson",
            "resultOffset":offset,
            "resultRecordCount":1000
        }

        r=requests.get(
            url,
            params=params,
            timeout=120
        )

        data=r.json()

        features=data.get("features",[])

        if not features:
            break


        for f in features:

            p=f["properties"]

            if source=="fairfax":

                name=p.get("FULLNAME")
                road_class=p.get("ROAD_CLASS")
                speed=p.get("SPEED_LIMIT_CAR")
                lanes=None

            elif source=="dc":

                name=p.get("STREETNAME")
                road_class=p.get("ROADTYPE")
                speed=p.get("SPEEDLIMITS_IB")
                lanes=p.get("TOTALTRAVELLANES")

            else:

                name=(
                    str(p.get("STREET_NAME",""))
                    +" "
                    +str(p.get("STREET_TYPE",""))
                )

                road_class=p.get("CFCC")
                speed=p.get("SPEED")
                lanes=None


            conn.execute("""
            INSERT INTO road_centerlines
            (
            source,
            road_name,
            road_class,
            speed_limit,
            lanes,
            geometry
            )
            VALUES (?,?,?,?,?,?)
            """,
            (
            source,
            name,
            road_class,
            speed,
            lanes,
            json.dumps(f["geometry"])
            ))


        total += len(features)

        print(source,total)

        offset += 1000


conn.commit()

print("Finished")
