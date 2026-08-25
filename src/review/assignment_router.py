import os
import sqlite3
import uuid
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB",
    BASE_DIR / "src" / "database" / "dmv_bus_stops.db",
))


def get_or_create_reviewer(reviewer_key=None):

    conn = sqlite3.connect(DB)

    cur = conn.cursor()


    if reviewer_key:

        existing = cur.execute(
            """
            SELECT id
            FROM community_reviewers
            WHERE reviewer_key=?
            """,
            (reviewer_key,)
        ).fetchone()


        if existing:

            conn.close()

            return existing[0], reviewer_key



    reviewer_key = uuid.uuid4().hex


    cur.execute(
        """
        INSERT INTO community_reviewers
        (
            reviewer_key
        )
        VALUES (?)
        """,
        (
            reviewer_key,
        )
    )


    reviewer_id = cur.lastrowid

    conn.commit()
    conn.close()


    return reviewer_id, reviewer_key



def stop_is_active(stop_id):

    conn = sqlite3.connect(DB)

    row = conn.execute(
        """
        SELECT physical_stop_id
        FROM stop_gtfs_status
        WHERE physical_stop_id=?
          AND current_gtfs=1
        """,
        (stop_id,)
    ).fetchone()

    conn.close()

    return row is not None



def assign_stop(
    reviewer_id,
    scenario,
    stop_id=None,
    latitude=None,
    longitude=None,
    campaign=None,
):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Previous assignments and proxy evidence never establish active status.
    if stop_id and not stop_is_active(stop_id):
        conn.close()
        return None

    # Return existing assignment if reviewer already has this stop assigned

    if stop_id:

        existing = cur.execute(
            """
            SELECT
                id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?
            AND reviewer_id=?
            AND status='assigned'

            LIMIT 1
            """,
            (
                stop_id,
                reviewer_id
            )
        ).fetchone()


        if existing:

            conn.close()

            return existing[0], existing[1]

    # -------------------------------------------------
    # Specific requested stop
    # -------------------------------------------------

    if stop_id:

        row = cur.execute(
            """
            SELECT
                rq.id,
                rq.physical_stop_id

            FROM review_queue rq

            JOIN stop_gtfs_status sgs
                ON sgs.physical_stop_id = rq.physical_stop_id
               AND sgs.current_gtfs = 1

            WHERE rq.physical_stop_id=?

            LIMIT 1
            """,
            (
                stop_id,
            )
        ).fetchone()



    # -------------------------------------------------
    # Route mode
    # -------------------------------------------------

    elif scenario == "route":

        row = cur.execute(
            """
            SELECT
                rq.id,
                rq.physical_stop_id

            FROM review_queue rq

            JOIN stop_gtfs_status sgs
                ON sgs.physical_stop_id = rq.physical_stop_id
               AND sgs.current_gtfs = 1

            JOIN physical_stop_members psm
                ON psm.physical_stop_id = rq.physical_stop_id

            JOIN stop_routes sr
                ON sr.stop_id = psm.bus_stop_id

            JOIN routes r
                ON r.id = sr.route_id

            JOIN community_reviewer_routes crr
                ON crr.route_id = r.route_id

            WHERE crr.reviewer_id = ?

            AND rq.review_status='pending'

            AND rq.community_review_available=1

            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE reviewer_id=?

            )

            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE status='assigned'

            )

            GROUP BY rq.physical_stop_id

            ORDER BY rq.priority_rank

            LIMIT 1

            """,
            (
                reviewer_id,
                reviewer_id
            )
        ).fetchone()



    # -------------------------------------------------
    # Nearby mode
    # -------------------------------------------------

    elif scenario == "nearby" and latitude and longitude:

        row = cur.execute(
            """
            SELECT
                rq.id,
                rq.physical_stop_id


            FROM review_queue rq

            JOIN stop_gtfs_status sgs
                ON sgs.physical_stop_id = rq.physical_stop_id
               AND sgs.current_gtfs = 1


            JOIN physical_stops ps

                ON ps.id = rq.physical_stop_id


            WHERE rq.review_status='pending'

            AND rq.community_review_available=1


            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE reviewer_id=?

            )


            ORDER BY

            (
                (ps.latitude - ?) *
                (ps.latitude - ?)

                +

                (ps.longitude - ?) *
                (ps.longitude - ?)

            )


            LIMIT 1
            """,
            (
                reviewer_id,
                latitude,
                latitude,
                longitude,
                longitude
            )
        ).fetchone()



    # -------------------------------------------------
    # Opportunity/default mode
    # -------------------------------------------------

    elif campaign in ("presence_verification", "seating_adequacy", "bench_clearance"):

        desired_state = {
            "presence_verification": "verify_presence",
            "seating_adequacy": "assess_adequacy",
            "bench_clearance": "collect_clearance_observation",
        }[campaign]
        row = cur.execute(
            """
            SELECT rq.id, rq.physical_stop_id
            FROM review_queue rq
            JOIN seating_improvement_opportunities sio
              ON sio.physical_stop_id=rq.physical_stop_id
            JOIN stop_gtfs_status sgs
              ON sgs.physical_stop_id=rq.physical_stop_id AND sgs.current_gtfs=1
            WHERE rq.review_status='pending' AND rq.community_review_available=1
              AND sio.workflow_state=?
              AND rq.physical_stop_id NOT IN
                  (SELECT stop_id FROM stop_review_assignments WHERE reviewer_id=?)
              AND rq.physical_stop_id NOT IN
                  (SELECT stop_id FROM stop_review_assignments WHERE status='assigned')
            ORDER BY sio.priority_score DESC, sio.physical_stop_id
            LIMIT 1
            """, (desired_state, reviewer_id)
        ).fetchone()

    else:

        row = cur.execute(
            """
            SELECT
                rq.id,
                rq.physical_stop_id


            FROM review_queue rq

            JOIN stop_gtfs_status sgs
                ON sgs.physical_stop_id = rq.physical_stop_id
               AND sgs.current_gtfs = 1


            LEFT JOIN opportunity_assessments oa

                ON oa.physical_stop_id = rq.physical_stop_id


            WHERE rq.review_status='pending'

            AND rq.community_review_available=1


            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE reviewer_id=?

            )


            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE status='assigned'

            )


            ORDER BY

                oa.combined_route_weekday_boardings DESC,

                rq.priority_rank ASC


            LIMIT 1

            """,
            (
                reviewer_id,
            )
        ).fetchone()



    if not row:

        conn.close()
        return None



    assigned_stop_id = row[1]


    assignment_columns = {
        item[1] for item in cur.execute("PRAGMA table_info(stop_review_assignments)")
    }
    if "campaign" in assignment_columns:
        cur.execute(
        """
        INSERT INTO stop_review_assignments
        (
            stop_id,
            reviewer_id,
            scenario,
            campaign,
            status
        )

        VALUES (?, ?, ?, ?, 'assigned')
        """,
        (
            assigned_stop_id,
            reviewer_id,
            scenario,
            campaign,
        )
        )
    else:
        cur.execute(
            "INSERT INTO stop_review_assignments(stop_id,reviewer_id,scenario,status) "
            "VALUES (?,?,?,'assigned')",
            (assigned_stop_id, reviewer_id, scenario),
        )


    assignment_id = cur.lastrowid


    conn.commit()
    conn.close()


    return assignment_id, assigned_stop_id
