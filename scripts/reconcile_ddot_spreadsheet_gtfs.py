import sqlite3
import math
import os
import requests
import pandas as pd


DB = "src/database/dmv_bus_stops.db"

SPREADSHEET = (
    "archive/data_backups/ddot_shelter_inventory.xlsx"
)

DDOT_API = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DDOT/Planning/FeatureServer/1/query"
)

OUTPUT = "ddot_spreadsheet_gtfs_reconciliation.csv"


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)

    a = (
        math.sin(dp/2)**2
        +
        math.cos(p1)
        *
        math.cos(p2)
        *
        math.sin(dl/2)**2
    )

    return R * 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1-a)
    )


def load_gtfs():

    conn = sqlite3.connect(DB)

    rows = conn.execute(
        """
        SELECT
            external_stop_id,
            stop_name,
            latitude,
            longitude
        FROM bus_stops
        """
    ).fetchall()

    conn.close()

    return rows


def nearest_gtfs(lat, lon, gtfs):

    best = None
    distance = None

    for stop in gtfs:

        d = haversine(
            lat,
            lon,
            stop[2],
            stop[3]
        )

        if distance is None or d < distance:
            distance = d
            best = stop

    return best, distance


def load_ddot_api():

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json"
    }

    data = requests.get(
        DDOT_API,
        params=params
    ).json()

    records = []

    for feature in data["features"]:

        attrs = feature["attributes"]
        geom = feature["geometry"]

        records.append(
            {
                "DDOT ID":
                    str(attrs.get("DDOT_ID")),

                "latitude":
                    geom["y"],

                "longitude":
                    geom["x"],

                "address":
                    attrs.get("Sales_Address")
            }
        )

    return records


def main():

    print("Loading spreadsheet...")

    sheet = pd.read_excel(
        SPREADSHEET
    )

    sheet["DDOT ID"] = (
        sheet["DDOT ID"]
        .astype(str)
        .str.replace(".0","")
    )

    print(
        "Spreadsheet shelters:",
        len(sheet)
    )


    print("Loading DDOT API...")

    api = load_ddot_api()

    api_df = pd.DataFrame(api)

    print(
        "API shelters:",
        len(api_df)
    )


    merged = sheet.merge(
        api_df,
        on="DDOT ID",
        how="outer",
        indicator=True
    )


    print()
    print("Spreadsheet only:",
          len(
              merged[
                  merged["_merge"]=="left_only"
              ]
          )
    )

    print(
        "API only:",
        len(
            merged[
                merged["_merge"]=="right_only"
            ]
        )
    )

    gtfs = load_gtfs()

    print(
        "GTFS stops:",
        len(gtfs)
    )


    results=[]


    for _, row in merged.iterrows():

        if pd.isna(row.get("latitude")):
            continue

        stop, distance = nearest_gtfs(
            row["latitude"],
            row["longitude"],
            gtfs
        )

        results.append(
            {
                "DDOT ID":
                    row["DDOT ID"],

                "Address":
                    row.get("Sales Address"),

                "Nearest GTFS":
                    stop[0],

                "GTFS Name":
                    stop[1],

                "Distance meters":
                    round(distance,2),

                "Within 25m":
                    distance <=25,

                "Within 50m":
                    distance <=50,

                "Within 100m":
                    distance <=100
            }
        )


    out = pd.DataFrame(results)

    out.to_csv(
        OUTPUT,
        index=False
    )

    print()
    print("GTFS reconciliation written:")
    print(OUTPUT)

    print()
    print(
        "Within 25m:",
        out["Within 25m"].sum()
    )

    print(
        "Within 50m:",
        out["Within 50m"].sum()
    )

    print(
        "Within 100m:",
        out["Within 100m"].sum()
    )


if __name__ == "__main__":
    main()