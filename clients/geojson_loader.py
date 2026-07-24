"""
Load WMATA Metrobus stop GeoJSON into canonical BusStop objects.
"""

from __future__ import annotations

import json
import requests 
from pathlib import Path
from typing import List

from dmv_bus_stops.models.stop import BusStop


# Default property mappings for the current WMATA export.
# These can be overridden if WMATA changes field names.
DEFAULT_FIELD_MAP = {
    "stop_id": "REG_ID",
    "stop_name": "NAME",
}"""
GeoJSON loading utilities.

Supports loading GeoJSON bus stop data
from local files or API endpoints.
"""

import json
import requests


def parse_geojson(
    data
):
    """
    Convert a GeoJSON FeatureCollection
    into a list of dictionaries.
    """

    features = data.get(
        "features",
        []
    )

    stops = []

    for feature in features:

        properties = feature.get(
            "properties",
            {}
        )

        geometry = feature.get(
            "geometry"
        )

        stop = properties.copy()

        if geometry:
            stop["geometry"] = geometry

        stops.append(
            stop
        )

    return stops



def load_geojson(
    filename
):
    """
    Load GeoJSON from a local file.
    """

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(
            file
        )

    return parse_geojson(
        data
    )



def load_geojson_url(
    url
):
    """
    Load GeoJSON from a URL/API endpoint.
    """

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return parse_geojson(
        data
    )



if __name__ == "__main__":

    import argparse


    parser = argparse.ArgumentParser()

    parser.add_argument(
        "geojson"
    )

    args = parser.parse_args()


    stops = load_geojson(
        args.geojson
    )


    print(
        f"Loaded {len(stops):,} bus stops."
    )


    if stops:

        print()

        print(
            "Example:"
        )

        print(
            stops[0]
        )
