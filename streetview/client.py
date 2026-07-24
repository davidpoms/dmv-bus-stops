"""
Google Street View client.

Responsible only for talking to the Street View API.
It does not know anything about databases, scoring, or volunteers.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import requests


METADATA_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
IMAGE_URL = "https://maps.googleapis.com/maps/api/streetview"


@dataclass
class Panorama:
    """
    Represents a Street View panorama.
    """

    pano_id: str

    latitude: float

    longitude: float

    status: str


class StreetViewClient:

    def __init__(
        self,
        api_key: str,
        image_size="640x640",
        fov=90,
        pitch=0,
    ):

        self.api_key = api_key

        self.image_size = image_size

        self.fov = fov

        self.pitch = pitch

    def metadata(self, latitude: float, longitude: float) -> Panorama | None:
        """
        Query Street View metadata.

        Returns
        -------
        Panorama
            if imagery exists.

        None
            if no imagery exists.
        """

        params = {
            "location": f"{latitude},{longitude}",
            "key": self.api_key,
        }

        r = requests.get(
            METADATA_URL,
            params=params,
            timeout=15,
        )

        r.raise_for_status()

        data = r.json()

        if data.get("status") != "OK":
            return None

        location = data.get("location", {})

        return Panorama(
            pano_id=data["pano_id"],
            latitude=location["lat"],
            longitude=location["lng"],
            status=data["status"],
        )

    def image_url(
        self,
        pano: Panorama,
        heading: float,
    ) -> str:
        """
        Build a Street View image URL.
        """

        params = {

            "size": self.image_size,

            "pano": pano.pano_id,

            "heading": heading,

            "pitch": self.pitch,

            "fov": self.fov,

            "key": self.api_key,
        }

        return f"{IMAGE_URL}?{urlencode(params)}"

    def has_imagery(
        self,
        latitude: float,
        longitude: float,
    ) -> bool:

        return self.metadata(latitude, longitude) is not None
