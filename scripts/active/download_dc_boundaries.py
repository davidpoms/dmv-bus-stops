import requests
from pathlib import Path


OUT = Path("data/geography")
OUT.mkdir(parents=True, exist_ok=True)


layers = {
    "dc_wards":
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Administrative_Other_Boundaries/MapServer/53/query",

    "dc_anc":
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Administrative_Other_Boundaries/MapServer/54/query",

    "dc_smd":
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Administrative_Other_Boundaries/MapServer/55/query",
}


for name,url in layers.items():

    print("Downloading", name)

    params = {
        "where":"1=1",
        "outFields":"*",
        "f":"geojson"
    }

    r=requests.get(
        url,
        params=params,
        timeout=120
    )

    print(r.status_code)

    r.raise_for_status()

    (OUT/f"{name}.geojson").write_text(
        r.text
    )


print("Done")
