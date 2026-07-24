import json
import requests


def load_geojson(filename):

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



def load_geojson_url(url):

    all_features = []

    offset = 0

    limit = 2000


    while True:

        response = requests.get(
            url,
            params={
                "resultOffset": offset,
                "resultRecordCount": limit,
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


        if len(features) < limit:

            break


        offset += limit


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


    print(
        f"Loaded {len(data.get('features', [])):,} features."
    )
