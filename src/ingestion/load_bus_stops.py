"""
DMV Bus Stops Intelligence Platform

Loads bus stops from a GeoJSON API,
normalizes fields, and prepares records
for database ingestion.
"""

from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[2]

sys.path.append(
    str(ROOT_DIR)
)


from src.config import BUS_STOP_API_URL
from clients.geojson_loader import load_geojson_url


STOP_FIELD_MAP = {

    "stop_id": [
        "REG_ID",
        "STOP_ID",
        "STOPID",
        "ID"
    ],

    "stop_name": [
        "BSTP_MSG_TEXT",
        "STOP_NAME",
        "NAME",
        "LOCATION"
    ],

    "route_id": [
        "ROUTEID",
        "ROUTES",
        "ROUTE"
    ],

    "direction": [
        "DIRECTION",
        "DIR"
    ],

    "street_name": [
        "AT_STR",
        "STREET",
        "STREET_NAME"
    ]

}


def find_first_property(
    properties,
    fields
):

    for field in fields:

        if field in properties:

            return properties[field]

    return None



def load_bus_stops(
    url=BUS_STOP_API_URL
):

    features = load_geojson_url(
        url
    )

    stops = []


    for feature in features:

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


        properties = feature.get(
            "properties",
            {}
        )


        stop = {

            "latitude": coordinates[1],

            "longitude": coordinates[0],

            "geometry": (
                coordinates[0],
                coordinates[1]
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

    return {

        "count": len(stops),

        "with_stop_id": sum(
            1
            for stop in stops
            if stop.get("stop_id")
        )

    }



if __name__ == "__main__":

    stops = load_bus_stops()

    print(
        f"Loaded {len(stops):,} bus stops."
    )

    print(
        summarize_bus_stops(
            stops
        )
    )

    if stops:

        print()

        print(
            stops[0]
        )
