import sqlite3
import pandas as pd
import requests
from difflib import SequenceMatcher
from math import radians, sin, cos, sqrt, atan2


XLSX = "archive/data_backups/ddot_shelter_inventory.xlsx"

API_URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)


DB = "src/database/dmv_bus_stops.db"


def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000

    p1 = radians(lat1)
    p2 = radians(lat2)

    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)

    a = (
        sin(dlat/2)**2 +
        cos(p1)*cos(p2)*sin(dlon/2)**2
    )

    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def similarity(a,b):
    if not a or not b:
        return 0

    return round(
        SequenceMatcher(
            None,
            str(a).lower(),
            str(b).lower()
        ).ratio(),
        3
    )


def load_api():

    params = {
        "where":"1=1",
        "outFields":"*",
        "returnGeometry":"true",
        "f":"json"
    }

    data = requests.get(
        API_URL,
        params=params
    ).json()

    rows=[]

    for f in data["features"]:

        a=f["attributes"]
        g=f["geometry"]

        rows.append({
            "api_id":str(
                a.get("DDOT_ID")
                or a.get("DDOT_SHELTER_ID")
            ),
            "api_address":
                a.get("Sales_Address"),
            "api_lat":
                g.get("y"),
            "api_lon":
                g.get("x")
        })

    return pd.DataFrame(rows)


def main():

    print("Loading spreadsheet...")

    sheet=pd.read_excel(XLSX)

    sheet.columns=[
        str(c).strip()
        for c in sheet.columns
    ]

    sheet=sheet.rename(
        columns={
            "DDOT ID":"spreadsheet_id",
            "Sales Address":"address",
            "Notes":"notes",
            "Barcode":"barcode"
        }
    )

    sheet["spreadsheet_id"] = (
        sheet["spreadsheet_id"]
        .astype(str)
        .str.strip()
    )

    print(
        "Spreadsheet:",
        len(sheet)
    )


    print("Loading API...")

    api=load_api()

    print(
        "API:",
        len(api)
    )


    results=[]


    used_api=set()


    for _,s in sheet.iterrows():

        sid=s["spreadsheet_id"]

        match=api[
            api.api_id==sid
        ]

        status=None
        aid=None
        dist=None
        sim=0


        if len(match):

            r=match.iloc[0]

            aid=r.api_id

            used_api.add(aid)

            if (
                "removed" in str(
                    s.notes
                ).lower()
            ):
                status="MATCHED_REMOVED"

            else:
                status="MATCHED_ACTIVE"


        else:

            best=None
            bestscore=0

            for _,a in api.iterrows():

                score=similarity(
                    s.address,
                    a.api_address
                )

                if score>bestscore:

                    bestscore=score
                    best=a


            if bestscore>=0.95:

                aid=best.api_id
                sim=bestscore

                used_api.add(aid)

                status="ID_CHANGED"

            else:

                status="SPREADSHEET_ONLY"



        results.append({

            "spreadsheet_id":sid,
            "api_id":aid,
            "barcode":
                s.get("barcode"),
            "address":
                s.get("address"),
            "notes":
                s.get("notes"),
            "status":status,
            "similarity":sim

        })


    for _,a in api.iterrows():

        if a.api_id not in used_api:

            results.append({

                "spreadsheet_id":None,
                "api_id":a.api_id,
                "barcode":None,
                "address":
                    a.api_address,
                "notes":None,
                "status":
                    "API_ONLY",
                "similarity":0
            })


    out=pd.DataFrame(results)

    out.to_csv(
        "ddot_lifecycle_reconciliation.csv",
        index=False
    )


    print()
    print(
        out.status.value_counts()
    )

    print(
        "\nWritten ddot_lifecycle_reconciliation.csv"
    )


if __name__=="__main__":
    main()