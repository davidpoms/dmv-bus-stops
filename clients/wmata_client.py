"""
WMATA API client.

Handles requests to WMATA
Open Data services.
"""

import requests


class WMATAClient:

    BASE_URL = "https://api.wmata.com"


    def __init__(
        self,
        api_key
    ):
        self.api_key = api_key


    def _get(
        self,
        endpoint
    ):
        """
        Internal GET helper.
        """

        response = requests.get(
            self.BASE_URL + endpoint,
            headers={
                "api_key": self.api_key
            }
        )

        response.raise_for_status()

        return response.json()


    def get_bus_stops(
        self
    ):
        """
        Retrieve Metrobus stops.
        """

        return self._get(
            "/Bus.svc/json/jStops"
        )
