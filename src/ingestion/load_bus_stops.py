"""
DMV Bus Stops Intelligence Platform

Bus stop ingestion module.

Purpose:
- Load WMATA bus stop GeoJSON files
- Normalize fields
- Produce consistent stop records
- Prepare data for database loading

This replaces the Colab notebook load_stops()
function and creates the foundation for all
downstream analysis.
"""


import json
from pathlib import Path
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.append(
    str(ROOT_DIR)
)

from config import BUS_STOP_FILE



# ------------------------------------------------------------
# Field mapping
#
# WMATA exports have changed over time.
# Keep this centralized so we can adjust without
# rewriting the pipeline.
# ------------------------------------------------------------

STOP_FIELD_MAP = {

    "stop_id": [
        "REG_ID",
        "STOP_ID",
        "STOPID",
        "ID"
    ],

    "stop_name": [
        "STOP_NAME",
        "NAME",
        "LOCATION"
    ],

    "route_id": [
        "ROUTES",
        "ROUTE",
    ],

    "direction": [
        "DIRECTION",
        "DIR"
    ],

    "street_name": [
        "STREET",
        "STREET_NAME"
    ]

}



def find_first_property(properties, possible_fields):

    """
    Find the first matching property name.

    Different WMATA exports have used
    different column names.
    """

    for field in possible_fields:

        if field in properties:

            return properties[field]


    return None




def load_bus_stops(filepath=BUS_STOP_FILE):

    """
    Load bus stops from GeoJSON.

    Returns:

    [
        {
            stop_id,
            latitude,
            longitude,
            stop_name,
            ...
        }
    ]

    """

    filepath = Path(filepath)


    if not filepath.exists():

        raise FileNotFoundError(
            f"Bus stop file not found: {filepath}"
        )



    with open(filepath, "r", encoding="utf-8") as f:

        geojson = json.load(f)



    stops = []



    for feature in geojson.get("features", []):


        geometry = feature.get("geometry")


        if not geometry:

            continue



        if geometry.get("type") != "Point":

            continue



        coordinates = geometry.get(
            "coordinates",
            []
        )


        if len(coordinates) < 2:

            continue



        longitude = coordinates[0]

        latitude = coordinates[1]



        properties = feature.get(
            "properties",
            {}
        )



        stop = {


            "latitude": latitude,


            "longitude": longitude,


            "geometry": (
                longitude,
                latitude
            )

        }



        # Normalize known fields

        for output_field, candidates in STOP_FIELD_MAP.items():

            stop[output_field] = find_first_property(
                properties,
                candidates
            )



        stops.append(stop)



    return stops




def summarize_bus_stops(stops):

    """
    Quick quality check.

    Useful before loading thousands of records.
    """

    print(
        f"Loaded {len(stops)} bus stops"
    )


    missing_ids = sum(
        1
        for stop in stops
        if not stop.get("stop_id")
    )


    print(
        f"Missing stop IDs: {missing_ids}"
    )



if __name__ == "__main__":


    stops = load_bus_stops()


    summarize_bus_stops(stops)
