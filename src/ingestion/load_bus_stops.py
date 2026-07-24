"""
DMV Bus Stops Intelligence Platform

Bus stop ingestion module.

Purpose:
- Load bus stop GeoJSON from API sources
- Normalize fields
- Produce consistent stop records
- Prepare data for database loading
"""

from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.append(
    str(ROOT_DIR)
)


from src.config import BUS_STOP_API_URL
from clients.geojson_loader import load_geojson_url



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
        "ROUTE"
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



def find_first_property(
    properties,
    possible_fields
):
    """
    Find the first matching property name.
    """

    for field in possible_fields:

        if field in properties:

            return properties[field]


    return None



def load_bus_stops(
    url=BUS_STOP_API_URL
):
    """
    Load bus stops from GeoJSON API.

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

    geojson = load_geojson_url(
        url
    )

    stops = []


    for feature in geojson.get(
        "features",
        []
    ):

        geometry = feature.get(
            "geometry"
        )


        if not geometry:

            continue


        if geometry.get(
            "type"
        ) != "Point":

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


        for output_field, candidates in STOP_FIELD_MAP.items():

            stop[output_field] = find_first_property(
                properties,
                candidates
            )


        stops.append(
            stop
        )


    return stops



def summarize_bus_stops(
    stops
):
    """
    Quick quality check.
    """

    return {

        "count": len(stops),

        "with_stop_id": sum(
            1
            for stop in stops
            if stop.get("stop_id")
        ),

        "with_coordinates": sum(
            1
            for stop in stops
            if stop.get("latitude")
            and stop.get("longitude")
        )

    }



if __name__ == "__main__":

    stops = load_bus_stops()


    print(
        f"Loaded {len(stops):,} bus stops."
    )


    print()

    print(
        summarize_bus_stops(
            stops
        )
    )


    if stops:

        print()

        print(
            "Example:"
        )

        print(
            stops[0]
        )
        if not stop.get("stop_id")
    )


    print(
        f"Missing stop IDs: {missing_ids}"
    )



if __name__ == "__main__":


    stops = load_bus_stops()


    summarize_bus_stops(stops)
