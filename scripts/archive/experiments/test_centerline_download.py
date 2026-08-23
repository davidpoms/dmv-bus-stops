import requests

urls = {
"fairfax":
"https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/OpenData_A1/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson",

"dc":
"https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Transportation_WebMercator/MapServer/163/query?outFields=*&where=1%3D1&f=geojson",

"montgomery":
"https://gis3.montgomerycountymd.gov/arcgis/rest/services/GDX/street_centerline/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
}

for name,url in urls.items():

    r=requests.get(url,timeout=60)

    print("\n",name)
    print("status:",r.status_code)

    data=r.json()

    print("keys:",data.keys())

    print("features:",len(data.get("features",[])))

    if data.get("features"):
        print("properties:")
        print(data["features"][0]["properties"].keys())
