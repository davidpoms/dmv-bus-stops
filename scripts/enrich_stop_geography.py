from pathlib import Path
import sqlite3

import geopandas as gpd
from shapely.geometry import Point


BASE = Path(__file__).resolve().parents[1]

DB = BASE / "src" / "database" / "dmv_bus_stops.db"

GEO = BASE / "data" / "geography"


def add_columns():

    conn = sqlite3.connect(DB)

    cols = {
        "state": "TEXT",
        "dc_ward": "TEXT",
        "dc_anc": "TEXT",
        "county": "TEXT",
        "municipality": "TEXT",
    }

    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(physical_stops)"
        )
    }

    for name, typ in cols.items():

        if name not in existing:
            conn.execute(
                f"""
                ALTER TABLE physical_stops
                ADD COLUMN {name} {typ}
                """
            )

    conn.commit()
    conn.close()


def load_stops():

    conn = sqlite3.connect(DB)

    df = gpd.GeoDataFrame(
        conn.execute(
            """
            SELECT
                id,
                latitude,
                longitude
            FROM physical_stops
            """
        ).fetchall(),
        columns=[
            "id",
            "latitude",
            "longitude",
        ],
        geometry=[
            Point(lon, lat)
            for lat, lon in conn.execute(
                """
                SELECT latitude, longitude
                FROM physical_stops
                """
            )
        ],
        crs="EPSG:4326",
    )

    conn.close()

    return df


def spatial_join(stops, boundary, column):

    boundary = gpd.read_file(boundary)

    joined = gpd.sjoin(
        stops,
        boundary[[column, "geometry"]],
        how="left",
        predicate="within",
    )

    return joined[column]


def main():

    add_columns()

    stops = load_stops()


    # Default state from jurisdiction if needed
    stops["state"] = ""


    print("Assigning DC wards...")

    stops["dc_ward"] = spatial_join(
        stops,
        GEO / "dc_wards.geojson",
        "WARD",
    )


    print("Assigning DC ANCs...")

    stops["dc_anc"] = spatial_join(
        stops,
        GEO / "dc_anc.geojson",
        "ANC_ID",
    )


    print("Assigning counties...")

    stops["county"] = spatial_join(
        stops,
        GEO / "md_va_counties.geojson",
        "NAME",
    )


    print("Assigning municipalities...")

    md_places = spatial_join(
        stops,
        GEO / "md_places.geojson",
        "NAME",
    )

    va_places = spatial_join(
        stops,
        GEO / "va_places.geojson",
        "NAME",
    )

    stops["municipality"] = (
        md_places
        .fillna(va_places)
    )


    # determine state
    stops.loc[
        stops["dc_ward"].notna(),
        "state"
    ] = "DC"

    stops.loc[
        stops["county"].notna()
        & stops["state"].eq(""),
        "state"
    ] = "MD/VA"


    conn = sqlite3.connect(DB)

    for _, row in stops.iterrows():

        conn.execute(
            """
            UPDATE physical_stops
            SET
                state=?,
                dc_ward=?,
                dc_anc=?,
                county=?,
                municipality=?
            WHERE id=?
            """,
            (
                row["state"],
                None if gpd.pd.isna(row["dc_ward"])
                else str(row["dc_ward"]),

                None if gpd.pd.isna(row["dc_anc"])
                else row["dc_anc"],

                None if gpd.pd.isna(row["county"])
                else row["county"],

                None if gpd.pd.isna(row["municipality"])
                else row["municipality"],

                row["id"],
            )
        )


    conn.commit()
    conn.close()


    print("Geography enrichment complete.")


if __name__ == "__main__":
    main()
