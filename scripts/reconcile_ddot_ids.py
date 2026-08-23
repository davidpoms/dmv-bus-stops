import pandas as pd
import requests


SHEET = "archive/data_backups/ddot_shelter_inventory.xlsx"

API = (
"https://maps2.dcgis.dc.gov/dcgis/rest/services/"
"DDOT/Planning/FeatureServer/1/query"
)


sheet = pd.read_excel(SHEET)

sheet_ids = set(
    sheet["DDOT ID"]
    .dropna()
    .astype(str)
    .str.replace(".0","")
)


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


api_ids=set()

for f in data["features"]:
    v=f["attributes"].get("DDOT_ID")
    if v:
        api_ids.add(str(v))


print("Spreadsheet IDs:", len(sheet_ids))
print("API IDs:", len(api_ids))

print()

print(
    "Shared:",
    len(sheet_ids & api_ids)
)

print(
    "Spreadsheet only:",
    len(sheet_ids-api_ids)
)

print(
    "API only:",
    len(api_ids-sheet_ids)
)


print()
print("Examples spreadsheet only:")
for x in list(sheet_ids-api_ids)[:20]:
    print(x)


print()
print("Examples API only:")
for x in list(api_ids-sheet_ids)[:20]:
    print(x)