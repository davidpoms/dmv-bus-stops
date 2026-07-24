"""
Initialize the DMV Bus Stops database.
"""

from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIR / "dmv_bus_stops.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def initialize_database():

    print("Creating database...")

    connection = sqlite3.connect(DATABASE_PATH)

    with open(SCHEMA_PATH, "r") as schema_file:
        schema = schema_file.read()

    connection.executescript(schema)

    connection.commit()
    connection.close()

    print("Database ready.")


if __name__ == "__main__":
    initialize_database()
