"""
Stop database queries.

Retrieves bus stop records and
associated intelligence signals.
"""


import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


class StopRepository:


    def __init__(
        self,
        database_path=DATABASE_PATH
    ):

        self.database_path = database_path



    def get_all_stops(
        self,
        limit=None
    ):
        """
        Retrieve bus stops.
        """


        connection = sqlite3.connect(
            self.database_path
        )

        cursor = connection.cursor()


        query = """
            SELECT *
            FROM bus_stops
        """


        if limit:

            query += f"""
            LIMIT {limit}
            """


        cursor.execute(
            query
        )


        stops = cursor.fetchall()


        connection.close()


        return stops



    def get_stop_observations(
        self,
        stop_id
    ):
        """
        Retrieve observations
        for a stop.
        """


        connection = sqlite3.connect(
            self.database_path
        )

        cursor = connection.cursor()


        cursor.execute(
            """
            SELECT *
            FROM stop_observations
            WHERE physical_stop_id = ?

            """,

            (
                stop_id,
            )
        )


        reviews = cursor.fetchall()


        connection.close()


        return reviews
