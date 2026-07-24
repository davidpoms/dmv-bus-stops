"""
Database repository layer.

Keeps SQL operations separate from business logic.

Future modules should call repositories rather than directly
writing SQL queries.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    """
    Lightweight database connection manager.

    Starts with SQLite for manual tracking and development.
    Can later be swapped for PostgreSQL/PostGIS without changing
    the rest of the application architecture.
    """

    def __init__(self, path: str = "dmv_bus_stops.db"):
        self.path = Path(path)

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self, schema_file: str):
        """
        Create tables from schema.sql.
        """

        with open(schema_file, "r", encoding="utf-8") as f:
            schema = f.read()

        with self.connect() as conn:
            conn.executescript(schema)


class StopRepository:
    """
    Handles bus stop records.
    """

    def __init__(self, database: Database):
        self.database = database

    def create(self, stop: Dict[str, Any]):
        """
        Add a new bus stop.
        """

        query = """
        INSERT INTO stops (
            stop_id,
            latitude,
            longitude,
            route,
            location_name
        )
        VALUES (?, ?, ?, ?, ?)
        """

        with self.database.connect() as conn:
            conn.execute(
                query,
                (
                    stop.get("stop_id"),
                    stop.get("latitude"),
                    stop.get("longitude"),
                    stop.get("route"),
                    stop.get("location_name"),
                ),
            )

    def get(self, stop_id: str) -> Optional[Dict]:
        """
        Retrieve a single stop.
        """

        query = """
        SELECT *
        FROM stops
        WHERE stop_id = ?
        """

        with self.database.connect() as conn:
            row = conn.execute(query, (stop_id,)).fetchone()

        return dict(row) if row else None

    def all(self) -> List[Dict]:
        """
        Retrieve every stop.
        """

        query = """
        SELECT *
        FROM stops
        """

        with self.database.connect() as conn:
            rows = conn.execute(query).fetchall()

        return [dict(row) for row in rows]


class ReviewRepository:
    """
    Handles volunteer reviews.
    """

    def __init__(self, database: Database):
        self.database = database

    def create(self, review: Dict[str, Any]):
        """
        Store a volunteer review.
        """

        query = """
        INSERT INTO reviews (
            stop_id,
            reviewer_id,
            has_shelter,
            has_bench,
            bench_candidate,
            flat_concrete_pad,
            curb_clearance_ok,
            bus_ramp_access_clear,
            where_people_wait,
            shade_available,
            reviewer_notes,
            reviewer_confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        with self.database.connect() as conn:
            conn.execute(
                query,
                (
                    review.get("stop_id"),
                    review.get("reviewer_id"),
                    review.get("has_shelter"),
                    review.get("has_bench"),
                    review.get("bench_candidate"),
                    review.get("flat_concrete_pad"),
                    review.get("curb_clearance_ok"),
                    review.get("bus_ramp_access_clear"),
                    review.get("where_people_wait"),
                    review.get("shade_available"),
                    review.get("reviewer_notes"),
                    review.get("reviewer_confidence"),
                ),
            )

    def for_stop(self, stop_id: str) -> List[Dict]:
        """
        Get all volunteer reviews for one stop.
        """

        query = """
        SELECT *
        FROM reviews
        WHERE stop_id = ?
        """

        with self.database.connect() as conn:
            rows = conn.execute(query, (stop_id,)).fetchall()

        return [dict(row) for row in rows]
