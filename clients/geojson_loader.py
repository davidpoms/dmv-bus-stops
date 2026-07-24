"""
GeoJSON loading utilities.

Supports loading GeoJSON bus stop data
from local files or API endpoints.
"""

import json
import requests


def parse_geojson(data):
    """
    Convert a GeoJSON FeatureCollection"""
GeoJSON loading utilities.

Supports:
- Local GeoJSON files
- GeoJSON API endpoints
- ArcGIS FeatureServer pagination
"""

import json
import requests



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

        return json.load(file)



def load_geojson_url(
    url
):
    """
    Load GeoJSON from an API endpoint.

    Handles ArcGIS-style pagination where
    responses are limited to 2,000 records.
    """

    all_features = []

    offset = 0

    page_size = 2000


    while True:

        response = requests.get(
            url,
            params={
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "f": "geojson"
            },
            timeout=60
        )


        response.raise_for_status()


        data = response.json()


        features = data.get(
            "features",
            []
        )


        if not features:

            break


        all_features.extend(
            features
        )


        if len(features) < page_size:

            break


        offset += page_size



    return {
        "features": all_features
    }



if __name__ == "__main__":

    import argparse


    parser = argparse.ArgumentParser()


    parser.add_argument(
        "geojson"
    )


    args = parser.parse_args()


    data = load_geojson(
        args.geojson
    )


    features = data.get(
        "features",
        []
    )


    print(
        f"Loaded {len(features):,} features."
    )


    if features:

        print()

        print(
            "Example:"
        )

        print(
            features[0]
        )
