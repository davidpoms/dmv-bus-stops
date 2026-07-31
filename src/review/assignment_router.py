"""
Volunteer assignment router.

Creates reviewer identities and assigns stops
based on dashboard scenarios.
"""

import sqlite3
import uuid
from pathlib import Path


DB = (
    Path(__file__).resolve()
    .parents[1]
    / "database"
    / "dmv_bus_stops.db"
)


# Minimum independent reviews before consensus
MIN_REVIEWERS = 3


def get_or_create_reviewer(reviewer_key=None):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()


    def stop_is_active(stop_id):

        row = cur.execute(
            """
            SELECT
                w.wmata_status
            FROM physical_stops p
            LEFT JOIN stop_wmata_evidence w
                ON p.id = w.physical_stop_id
            WHERE p.id=?
            """,
            (stop_id,)
        ).fetchone()


        if not row:
            return True


        status = row[0]

        return status != "ABS"


    if reviewer_key:

        row = cur.execute(
            """
            SELECT id
            FROM community_reviewers
            WHERE reviewer_key=?
            """,
            (reviewer_key,)
        ).fetchone()

        if row:
            conn.close()
            return row[0], reviewer_key


    new_key = (
        "reviewer_"
        +
        uuid.uuid4().hex[:8]
    )

    cur.execute(
        """
        INSERT INTO community_reviewers
        (
            reviewer_key,
            display_name
        )
        VALUES (?,?)
        """,
        (
            new_key,
            "Community Reviewer"
        )
    )

    reviewer_id = cur.lastrowid

    conn.commit()
    conn.close()

    return reviewer_id, new_key



def stop_is_active(stop_id):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT
            wmata_status
        FROM stop_wmata_evidence
        WHERE physical_stop_id=?
        """,
        (stop_id,)
    ).fetchone()

    conn.close()

    if not row:
        return True

    status = row[0]

    # WMATA statuses:
    # PRS = published/active stop
    # ABS = abandoned/inactive stop
    # Other unknown values are allowed for now

    if status == "ABS":
        return False

    return True



def assign_stop(
    reviewer_id,
    scenario,
    stop_id=None,
    latitude=None,
    longitude=None
):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    existing = cur.execute(
        """
        SELECT
            id,
            stop_id
        FROM stop_review_assignments
        WHERE reviewer_id=?
        AND scenario=?
        AND status='assigned'
        ORDER BY id DESC
        LIMIT 1
        """ ,
        (
            reviewer_id,
            scenario
        )
    ).fetchone()


    if existing and scenario == "opportunity":

        status = cur.execute(
            "SELECT status FROM stop_review_assignments WHERE id=?",
            (existing[0],)
        ).fetchone()


        if status and status[0] == "assigned":
            conn.close()
            return existing[0], existing[1]


    if stop_id:

        if not stop_is_active(stop_id):
            conn.close()
            return None

        stop = (
            stop_id,
        )


    elif scenario == "opportunity":

        stop = cur.execute(
            """
            SELECT rq.physical_stop_id
            FROM review_queue rq
            LEFT JOIN stop_wmata_evidence w
                ON rq.physical_stop_id = w.physical_stop_id

            WHERE rq.verification_needed=1

            AND (
                w.wmata_status IS NULL
                OR w.wmata_status != 'ABS'
            )

            AND rq.physical_stop_id NOT IN
            (
                SELECT stop_id
                FROM stop_review_assignments
                WHERE reviewer_id=?
                AND status='completed'
            )

            ORDER BY rq.priority_rank
            LIMIT 1
            """,
            (reviewer_id,)
        ).fetchone()


    elif scenario == "nearby":

        # Use provided coordinates when available.
        # Fall back to highest priority nearby-capable stop.
        stop = cur.execute(
            """
            SELECT
                rq.physical_stop_id
            FROM review_queue rq
            JOIN physical_stops ps
                ON ps.id = rq.physical_stop_id
            LEFT JOIN stop_wmata_evidence w
                ON rq.physical_stop_id = w.physical_stop_id
            WHERE rq.community_review_available=1
            AND (
                w.wmata_status IS NULL
                OR w.wmata_status != 'ABS'
            )
            ORDER BY
                CASE
                    WHEN ? IS NOT NULL AND ? IS NOT NULL THEN
                        (
                            (ps.latitude - ?) * (ps.latitude - ?)
                            +
                            (ps.longitude - ?) * (ps.longitude - ?)
                        )
                    ELSE rq.priority_rank
                END
            LIMIT 1
            """
        ,
        (
            latitude,
            longitude,
            latitude,
            latitude,
            longitude,
            longitude
        )
        ).fetchone()


    elif scenario == "route":

        # Route filtering requires a stop_routes table.
        # Until route data is loaded, use highest priority available stop.
        stop = cur.execute(
            """
            SELECT rq.physical_stop_id
            FROM review_queue rq
            LEFT JOIN stop_wmata_evidence w
                ON rq.physical_stop_id = w.physical_stop_id
            WHERE rq.community_review_available=1
            AND (
                w.wmata_status IS NULL
                OR w.wmata_status != 'ABS'
            )
            ORDER BY rq.priority_rank
            LIMIT 1
            """
        ).fetchone()


    else:

        raise ValueError(
            "Unknown scenario"
        )


    if not stop:

        conn.close()
        return None


    stop_id = stop[0]


    cur.execute(
        """
        INSERT INTO stop_review_assignments
        (
            stop_id,
            reviewer_id,
            scenario
        )
        VALUES (?, ?, ?)
        """,
        (
            stop_id,
            reviewer_id,
            scenario
        )
    )


    assignment = cur.execute(
        """
        SELECT id
        FROM stop_review_assignments
        WHERE stop_id=?
        AND reviewer_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            stop_id,
            reviewer_id
        )
    ).fetchone()


    conn.commit()
    conn.close()


    return assignment[0], stop_id
