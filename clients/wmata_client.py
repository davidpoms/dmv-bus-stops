"""
WMATA API client.

Handles communication with
WMATA open data services.
"""


import requests


class WMATAClient:


    def __init__(
        self,
        api_key=None
    ):
        self.api_key = api_key


    def get_bus_stops(
        self
    ):
        """
        Retrieve Metrobus stops.

        Placeholder until the exact
        WMATA endpoint is configured.
        """

        if not self.api_key:
            raise ValueError(
                "WMATA API key required"
            )


        headers = {
            "api_key": self.api_key
        }


        response = requests.get(
            "https://api.wmata.com/Bus.svc/json/jStops",
            headers=headers
        )


        response.raise_for_status()


        return response.json()
