import pandas as pd
import requests
from difflib import SequenceMatcher


SHEET = "archive/data_backups/ddot_shelter_inventory.xlsx"

API = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DDOT/Planning/FeatureServer/1/query"
)


def normalize(x):
    if not isinstance(x, str):
        return ""

    return (
        x.lower()
        .replace('"', "")
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace("-", " ")
        .strip()
    )


def similarity(a,b):
    return SequenceMatcher(
        None,
        normalize(a),
        normalize(b)
    ).ratio()


print("Loading spreadsheet")

sheet = pd.read_excel(SHEET)

sheet["DDOT ID"] = (
    sheet["DDOT ID"]
    .astype(str)
    .str.replace(".0","")
)


print("Loading API")

params = {
    "where":"1=1",
    "outFields":"*",
    "returnGeometry":"false",
    "f":"json"
}

data = requests.get(
    API,
    params=params
).json()


api=[]

for f in data["features"]:
    a=f["attributes"]

    api.append(
        {
            "id":str(a.get("DDOT_ID")),
            "address":a.get("Sales_Address")
        }
    )


api_df=pd.DataFrame(api)


missing = sheet[
    ~sheet["DDOT ID"].isin(
        api_df["id"]
    )
]


print(
    "Spreadsheet IDs missing from API:",
    len(missing)
)


for _,row in missing.head(25).iterrows():

    best=None
    score=0

    for _,a in api_df.iterrows():

        s=similarity(
            row["Sales Address"],
            a["address"]
        )

        if s>score:
            score=s
            best=a


    print()
    print("Spreadsheet:")
    print(row["DDOT ID"])
    print(row["Sales Address"])

    print("Best API:")
    print(best["id"])
    print(best["address"])

    print(
        "Similarity:",
        round(score,3)
    )