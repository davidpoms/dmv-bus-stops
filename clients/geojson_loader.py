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
}


def load_geojson(
    filename: str | Path,
    field_map: dict | None = None,
) -> List[BusStop]:
    """
    Load a GeoJSON FeatureCollection and return BusStop objects.

    Parameters
    ----------
    filename
        Path to the WMATA bus stop GeoJSON.

    field_map
        Mapping between BusStop fields and GeoJSON property names.

    Returns
    -------
    list[BusStop]
    """

    field_map = field_map or DEFAULT_FIELD_MAP

    with open(filename, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    features = geojson.get("features", [])

    stops: List[BusStop] = []

    for feature in features:

        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})

        if geometry.get("type") != "Point":
            continue

        coordinates = geometry.get("coordinates", [])

        if len(coordinates) < 2:
            continue

        lon = coordinates[0]
        lat = coordinates[1]

        stop = BusStop(
            stop_id=str(properties.get(field_map["stop_id"], "")),
            stop_name=properties.get(field_map["stop_name"]),
            latitude=lat,
            longitude=lon,
        )

        stops.append(stop)

    return stops

def load_geojson_url(
    url
):
    """
    Load GeoJSON from an API endpoint.
    """

    response = requests.get(
        url
    )

    response.raise_for_status()

    data = response.json()

    return [
        feature["properties"]
        | {
            "geometry": feature.get(
                "geometry"
            )
        }
        for feature in data["features"]
    ]
def load_single_stop(
    filename: str | Path,
    stop_id: str,
) -> BusStop | None:
    """
    Convenience function for loading one stop by ID.
    """

    for stop in load_geojson(filename):
        if stop.stop_id == stop_id:
            return stop

    return None


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("geojson")

    args = parser.parse_args()

    stops = load_geojson(args.geojson)

    print(f"Loaded {len(stops):,} bus stops.")

    if stops:
        print()
        print("Example:")
        print(stops[0])
