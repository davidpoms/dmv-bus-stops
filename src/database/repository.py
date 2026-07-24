"""
Database repository methods.

Handles saving and retrieving
bus stop intelligence.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR /
    "src" /
    "database" /
    "dmv_bus_stops.db"
)



class Repository:


    def __init__(
        self,
        database_path=DATABASE_PATH
    ):

        self.database_path = database_path



    def save_review(
        self,
        review
    ):
        """
        Save volunteer feedback.
        """


        connection = sqlite3.connect(
            self.database_path
        )

        cursor = connection.cursor()


        cursor.execute(
            """
            INSERT INTO stop_reviews
            (
                stop_id,
                reviewer_type,
                review_data,
                confidence,
                created_at
            )

            VALUES (?, ?, ?, ?, ?)

            """,

            (
                review["stop_id"],
                "volunteer",
                str(review),
                review.get(
                    "review_confidence",
                    0
                ),
                datetime.utcnow()
            )
        )


        connection.commit()

        connection.close()



    def get_reviews_for_stop(
        self,
        stop_id
    ):
        """
        Retrieve all reviews
        for a stop.
        """


        connection = sqlite3.connect(
            self.database_path
        )

        cursor = connection.cursor()


        cursor.execute(
            """
            SELECT *
            FROM stop_reviews
            WHERE stop_id = ?

            """,

            (
                stop_id,
            )
        )


        reviews = cursor.fetchall()


        connection.close()


        return reviews
