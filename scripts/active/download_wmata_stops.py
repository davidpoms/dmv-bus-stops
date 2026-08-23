import requests
import pandas as pd
from pathlib import Path
import time


URL = (
    "https://gisservices.wmata.com/gisservices/rest/services/"
    "Public/MBSI_MAP_WMS/MapServer/11/query"
)

log = []

OUT = Path("data/wmata_bus_stops_raw.csv")


def query_range(start, end):

    params = {
        "where": f"OBJECTID >= {start} AND OBJECTID < {end}",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json"
    }

    try:
        r = requests.get(
            URL,
            params=params,
            timeout=60
        )

        data = r.json()

    except Exception as e:
        print("REQUEST FAILED:", start, end, e)
        return None


    if "error" in data:
        return None


    return data.get(
        "features",
        []
    )


def download_range(start, end):

    features = query_range(
        start,
        end
    )

    if features is not None:
        print(
            f"OK {start}-{end}: {len(features)}"
        )
        return features


    # failed, split it
    size = end - start

    if size <= 1:
        print(
            "SKIP",
            start
        )
        return []


    mid = start + size // 2

    print(
        f"SPLIT FAILED RANGE {start}-{end}"
    )

    left = download_range(
        start,
        mid
    )

    right = download_range(
        mid,
        end
    )

    return left + right



if __name__ == "__main__":

    rows = []

    MAX_OBJECTID = 9000

    STEP = 250


    for start in range(
        1,
        MAX_OBJECTID,
        STEP
    ):

        end = min(
            start + STEP,
            MAX_OBJECTID
        )

        print(
            "\nRANGE:",
            start,
            end
        )

        features = download_range(
            start,
            end
        )

        rows.extend(
            [
                f["attributes"]
                for f in features
            ]
        )

        print(
            "TOTAL:",
            len(rows)
        )

        time.sleep(
            0.5
        )


    df = pd.DataFrame(rows)


    if "OBJECTID" in df.columns:
        df = df.drop_duplicates(
            subset=["OBJECTID"]
        )


    OUT.parent.mkdir(
        exist_ok=True
    )

    df.to_csv(
        OUT,
        index=False
    )

    print("\nDONE")
    print(
        "Saved:",
        OUT
    )
    print(
        "Rows:",
        len(df)
    )


# Write failed ranges after completion
with open("data/wmata_failed_ranges.log", "w") as f:
    for item in log:
        f.write(f"{item[0]}-{item[1]}\\n")
