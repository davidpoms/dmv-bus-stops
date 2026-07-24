"""
WMATA GTFS static feed client.

Downloads the GTFS ZIP using the WMATA API key.
"""

import io
import zipfile
import requests

from src.config import WMATA_API_KEY


GTFS_URL = (
    "https://api.wmata.com/gtfs/bus-gtfs-static.zip"
)



def download_gtfs():

    response = requests.get(
        GTFS_URL,
        headers={
            "api_key": WMATA_API_KEY
        }
    )

    response.raise_for_status()

    return zipfile.ZipFile(
        io.BytesIO(response.content)
    )
