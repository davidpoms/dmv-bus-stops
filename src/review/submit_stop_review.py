"""
Submit a completed volunteer stop review.

Writes field observations into stop_observations.
"""

import sqlite3
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    /
    "src"
    /
    "database"
    /
    "dmv_bus_stops.db"
)


def submit_review(review_file):

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    data = json.loads(
        Path(review_file).read_text()
    )

    cursor.execute(
        """
        INSERT INTO stop_observations (

            physical_stop_id,

            reviewer_id,

            shelter_present,

            bench_present,

            bench_condition,

            waiting_area_type,

            likely_waiting_location,

            sun_exposure,

            concrete_pad_present,

            pad_width_feet,

            pad_depth_feet,

            bench_feasible,

            curb_access_clear,

            bus_ramp_access_clear,

            landing_zone_clear,

            rear_clear_zone_clear,

            confidence,

            notes

        )

        VALUES (

            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?

        );

        """,
        (

            data["stop_id"],

            data.get("reviewer_id"),

            data.get("shelter_present"),

            data.get("bench_present"),

            data.get("bench_condition"),

            data.get("waiting_area_type"),

            data.get("likely_waiting_location"),

            data.get("sun_exposure"),

            data.get("concrete_pad_present"),

            data.get("pad_width_feet"),

            data.get("pad_depth_feet"),

            data.get("bench_feasible"),

            data.get("curb_access_clear"),

            data.get("bus_ramp_access_clear"),

            data.get("landing_zone_clear"),

            data.get("rear_clear_zone_clear"),

            data.get("confidence"),

            data.get("notes")

        )

    )

    conn.commit()

    review_id = cursor.lastrowid

    conn.close()

    print(
        f"Created stop review {review_id}"
    )


if __name__ == "__main__":

    submit_review(
        "sample_review.json"
    )
