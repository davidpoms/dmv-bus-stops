import sqlite3
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pathlib import Path


DB = "src/database/dmv_bus_stops.db"

GEO = Path("data/geography")


conn = sqlite3.connect(DB)


# ----------------------------
# Load stops
# ----------------------------

stops = pd.read_sql(
    """
    SELECT
        id,
        latitude,
        longitude
    FROM physical_stops
    """,
    conn
)


gdf = gpd.GeoDataFrame(
    stops,
    geometry=[
        Point(xy)
        for xy in zip(
            stops.longitude,
            stops.latitude
        )
    ],
    crs="EPSG:4326"
)


# ----------------------------
# Base output
# ----------------------------

out = gdf[
    ["id"]
].copy()

out.rename(
    columns={
        "id":"stop_id"
    },
    inplace=True
)

out["state"] = None
out["county"] = None
out["municipality"] = None
out["municipality_type"] = None
out["county_fips"] = None
out["place_fips"] = None

out["dc_ward"] = None
out["dc_anc"] = None
out["dc_smd"] = None


# ----------------------------
# Counties
# ----------------------------

counties = gpd.read_file(
    GEO/"md_va_counties.geojson"
)

counties = counties.to_crs(
    gdf.crs
)


county_join = gpd.sjoin(
    gdf,
    counties,
    predicate="intersects",
    how="left"
)


for idx,row in county_join.iterrows():

    if pd.notna(row.get("NAME")):

        out.loc[
            out.stop_id==row.id,
            "county"
        ] = row.NAME

        out.loc[
            out.stop_id==row.id,
            "county_fips"
        ] = (
            str(row.STATEFP)
            +
            str(row.COUNTYFP)
        )

        if row.STATEFP=="24":
            out.loc[
                out.stop_id==row.id,
                "state"
            ]="MD"

        elif row.STATEFP=="51":
            out.loc[
                out.stop_id==row.id,
                "state"
            ]="VA"



# ----------------------------
# District of Columbia
# ----------------------------

dc_boundary = gpd.read_file(
    GEO/"dc_wards.geojson"
).to_crs(
    gdf.crs
)

dc_join = gpd.sjoin(
    gdf,
    dc_boundary[["geometry"]],
    predicate="intersects",
    how="inner"
)

dc_ids = gdf.loc[
    dc_join.index.unique(),
    "id"
]

out.loc[
    out.stop_id.isin(dc_ids),
    "state"
] = "DC"

out.loc[
    out.stop_id.isin(dc_ids),
    "county"
] = "District of Columbia"

# Remove Maryland/Virginia place assignments from DC stops
out.loc[
    out.stop_id.isin(dc_ids),
    [
        "municipality",
        "municipality_type",
        "county_fips",
        "place_fips"
    ]
] = None


# ----------------------------
# Maryland places
# ----------------------------

md_places=gpd.read_file(
    GEO/"md_places.geojson"
).to_crs(
    gdf.crs
)


join=gpd.sjoin(
    gdf,
    md_places,
    predicate="intersects",
    how="inner"
)


for idx,row in join.iterrows():

    out.loc[
        out.stop_id==row.id,
        "municipality"
    ] = row.NAME

    out.loc[
        out.stop_id==row.id,
        "municipality_type"
    ] = "place"

    out.loc[
        out.stop_id==row.id,
        "place_fips"
    ] = (
        str(row.STATEFP)
        +
        str(row.PLACEFP)
    )



# ----------------------------
# Virginia places
# ----------------------------

va_places=gpd.read_file(
    GEO/"va_places.geojson"
).to_crs(
    gdf.crs
)


join=gpd.sjoin(
    gdf,
    va_places,
    predicate="intersects",
    how="inner"
)


for idx,row in join.iterrows():

    out.loc[
        out.stop_id==row.id,
        "municipality"
    ] = row.NAME

    out.loc[
        out.stop_id==row.id,
        "municipality_type"
    ]="place"

    out.loc[
        out.stop_id==row.id,
        "place_fips"
    ]=(
        str(row.STATEFP)
        +
        str(row.PLACEFP)
    )



# ----------------------------
# DC layers

dc_boundary = gpd.read_file(
    GEO/"dc_wards.geojson"
).to_crs(
    gdf.crs
)

dc_join = gpd.sjoin(
    gdf,
    dc_boundary[["geometry"]],
    predicate="intersects",
    how="inner"
)

dc = gdf.loc[
    dc_join.index
]

def apply_dc_layer(filename,column,field):

    layer=gpd.read_file(
        GEO/filename
    ).to_crs(
        gdf.crs
    )

    join=gpd.sjoin(
        dc,
        layer,
        predicate="intersects",
        how="left"
    )

    for idx,row in join.iterrows():

        if pd.notna(row.get(field)):

            out.loc[
                out.stop_id==row.id,
                column
            ]=str(row[field])


apply_dc_layer(
    "dc_wards.geojson",
    "dc_ward",
    "WARD"
)

apply_dc_layer(
    "dc_anc.geojson",
    "dc_anc",
    "ANC_ID"
)

apply_dc_layer(
    "dc_smd.geojson",
    "dc_smd",
    "SMD_ID"
)



# ----------------------------
# Final DC cleanup
# ----------------------------

out.loc[
    out.state=="DC",
    [
        "municipality",
        "municipality_type",
        "county_fips",
        "place_fips"
    ]
] = None


# ----------------------------
# Save
# ----------------------------

out.to_sql(
    "stop_jurisdiction",
    conn,
    if_exists="append",
    index=False
)


conn.commit()

print(
    "Enriched",
    len(out),
    "stops"
)
