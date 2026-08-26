import sqlite3
import shutil
import os
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", ROOT / "src" / "database" / "dmv_bus_stops.db"
))


def table_exists(conn, table_name):
    return (
        conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (table_name,),
        ).fetchone()
        is not None
    )


def main():

    if not DB.exists():
        raise FileNotFoundError(
            f"Database not found: {DB}"
        )

    print("Database:", DB)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    try:

        # --------------------------------------------------
        # 1. Verify required tables
        # --------------------------------------------------

        required_tables = [
            "physical_stops",
            "physical_stop_members",
            "bus_stops",
            "gtfs_stop_map",
            "stop_routes",
            "routes",
        ]

        missing = [
            table
            for table in required_tables
            if not table_exists(conn, table)
        ]

        if missing:
            raise RuntimeError(
                "Missing required tables: "
                + ", ".join(missing)
            )

        print("\nRequired tables: OK")


        # --------------------------------------------------
        # 2. Calculate expected status BEFORE changing DB
        # --------------------------------------------------

        expected_current = conn.execute(
            """
            SELECT COUNT(DISTINCT psm.physical_stop_id)

            FROM physical_stop_members psm

            JOIN gtfs_stop_map gm
                ON gm.bus_stop_id = psm.bus_stop_id
            """
        ).fetchone()[0]


        expected_route_served = conn.execute(
            """
            SELECT COUNT(DISTINCT psm.physical_stop_id)

            FROM physical_stop_members psm

            JOIN gtfs_stop_map gm
                ON gm.bus_stop_id = psm.bus_stop_id

            JOIN stop_routes sr
                ON sr.stop_id = gm.bus_stop_id
            """
        ).fetchone()[0]


        expected_not_current = conn.execute(
            """
            SELECT COUNT(*)

            FROM physical_stops ps

            WHERE NOT EXISTS (
                SELECT 1

                FROM physical_stop_members psm

                JOIN gtfs_stop_map gm
                    ON gm.bus_stop_id = psm.bus_stop_id

                WHERE psm.physical_stop_id = ps.id
            )
            """
        ).fetchone()[0]


        physical_stop_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM physical_stops
            """
        ).fetchone()[0]


        print("\nExpected status:")
        print(
            "Physical stops:",
            physical_stop_count
        )
        print(
            "Currently represented in GTFS:",
            expected_current
        )
        print(
            "Currently route-served:",
            expected_route_served
        )
        print(
            "Not currently represented in GTFS:",
            expected_not_current
        )


        # --------------------------------------------------
        # 3. Sanity checks
        # --------------------------------------------------

        if expected_current == 0:
            raise RuntimeError(
                "No physical stops are represented in GTFS. "
                "Aborting."
            )


        if expected_current > physical_stop_count:
            raise RuntimeError(
                "Current GTFS physical-stop count exceeds "
                "physical_stops count. Aborting."
            )


        if expected_current + expected_not_current != physical_stop_count:
            raise RuntimeError(
                "Current + not-current counts do not equal "
                "physical_stops count. Aborting."
            )


        # --------------------------------------------------
        # 4. Create database backup
        # --------------------------------------------------

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_path = DB.with_name(
            f"{DB.stem}_before_gtfs_status_"
            f"{timestamp}{DB.suffix}"
        )

        print(
            "\nCreating database backup:",
            backup_path
        )

        shutil.copy2(
            DB,
            backup_path
        )

        print("Backup created.")


        # --------------------------------------------------
        # 5. Begin transaction
        # --------------------------------------------------

        conn.execute("BEGIN")


        # --------------------------------------------------
        # 6. Create dedicated status table
        # --------------------------------------------------

        conn.execute(
            """
            DROP TABLE IF EXISTS stop_gtfs_status
            """
        )


        conn.execute(
            """
            CREATE TABLE stop_gtfs_status
            (
                physical_stop_id INTEGER PRIMARY KEY,

                current_gtfs INTEGER NOT NULL,

                route_served INTEGER NOT NULL,

                gtfs_stop_count INTEGER NOT NULL,

                route_count INTEGER NOT NULL,

                status TEXT NOT NULL,

                source TEXT NOT NULL,

                checked_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # --------------------------------------------------
        # 7. Populate status table
        # --------------------------------------------------

        conn.execute(
            """
            INSERT INTO stop_gtfs_status
            (
                physical_stop_id,
                current_gtfs,
                route_served,
                gtfs_stop_count,
                route_count,
                status,
                source
            )

            SELECT
                ps.id,

                CASE
                    WHEN COUNT(DISTINCT gm.gtfs_stop_id) > 0
                    THEN 1
                    ELSE 0
                END AS current_gtfs,

                CASE
                    WHEN COUNT(DISTINCT sr.id) > 0
                    THEN 1
                    ELSE 0
                END AS route_served,

                COUNT(DISTINCT gm.gtfs_stop_id)
                    AS gtfs_stop_count,

                COUNT(DISTINCT r.id)
                    AS route_count,

                CASE
                    WHEN COUNT(DISTINCT gm.gtfs_stop_id) > 0
                    THEN 'current'
                    ELSE 'not_current'
                END AS status,

                'WMATA current GTFS stops.txt'
                    AS source

            FROM physical_stops ps

            LEFT JOIN physical_stop_members psm
                ON psm.physical_stop_id = ps.id

            LEFT JOIN gtfs_stop_map gm
                ON gm.bus_stop_id = psm.bus_stop_id

            LEFT JOIN stop_routes sr
                ON sr.stop_id = psm.bus_stop_id

            LEFT JOIN routes r
                ON r.id = sr.route_id

            GROUP BY ps.id
            """
        )


        # --------------------------------------------------
        # 8. Validate row count
        # --------------------------------------------------

        actual_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM stop_gtfs_status
            """
        ).fetchone()[0]


        print(
            "\nStatus table rows:",
            actual_rows
        )


        if actual_rows != physical_stop_count:
            raise RuntimeError(
                "Status table row count does not match "
                "physical_stops."
            )


        # --------------------------------------------------
        # 9. Validate current count
        # --------------------------------------------------

        actual_current = conn.execute(
            """
            SELECT COUNT(*)
            FROM stop_gtfs_status
            WHERE current_gtfs = 1
            """
        ).fetchone()[0]


        actual_route_served = conn.execute(
            """
            SELECT COUNT(*)
            FROM stop_gtfs_status
            WHERE route_served = 1
            """
        ).fetchone()[0]


        actual_not_current = conn.execute(
            """
            SELECT COUNT(*)
            FROM stop_gtfs_status
            WHERE current_gtfs = 0
            """
        ).fetchone()[0]


        print(
            "Current GTFS:",
            actual_current
        )

        print(
            "Route-served:",
            actual_route_served
        )

        print(
            "Not current:",
            actual_not_current
        )


        if actual_current != expected_current:
            raise RuntimeError(
                "Current-GTFS validation failed: "
                f"expected {expected_current}, "
                f"got {actual_current}"
            )


        if actual_route_served != expected_route_served:
            raise RuntimeError(
                "Route-served validation failed: "
                f"expected {expected_route_served}, "
                f"got {actual_route_served}"
            )


        if actual_not_current != expected_not_current:
            raise RuntimeError(
                "Not-current validation failed: "
                f"expected {expected_not_current}, "
                f"got {actual_not_current}"
            )


        # --------------------------------------------------
        # 10. Validate status consistency
        # --------------------------------------------------

        inconsistent = conn.execute(
            """
            SELECT COUNT(*)

            FROM stop_gtfs_status

            WHERE
                (
                    current_gtfs = 1
                    AND status != 'current'
                )

                OR

                (
                    current_gtfs = 0
                    AND status != 'not_current'
                )
            """
        ).fetchone()[0]


        if inconsistent != 0:
            raise RuntimeError(
                "Status consistency validation failed."
            )


        # --------------------------------------------------
        # 11. Validate route-served implies current GTFS
        # --------------------------------------------------

        invalid_route_status = conn.execute(
            """
            SELECT COUNT(*)

            FROM stop_gtfs_status

            WHERE route_served = 1
              AND current_gtfs = 0
            """
        ).fetchone()[0]


        if invalid_route_status != 0:
            raise RuntimeError(
                "A route-served stop was found without "
                "current GTFS status."
            )


        # --------------------------------------------------
        # 12. Commit
        # --------------------------------------------------

        conn.commit()


        print("\n===================================")
        print("GTFS STOP STATUS BUILD SUCCESSFUL")
        print("===================================")

        print(
            "Physical stops:",
            physical_stop_count
        )

        print(
            "Currently represented in GTFS:",
            actual_current
        )

        print(
            "Currently route-served:",
            actual_route_served
        )

        print(
            "Not currently represented in GTFS:",
            actual_not_current
        )

        print(
            "Database backup:",
            backup_path
        )

        print("\nNo validation errors.")


    except Exception:

        print(
            "\nERROR: GTFS status build failed."
        )

        print(
            "Rolling back transaction..."
        )

        conn.rollback()

        print(
            "The new status table was NOT left "
            "in a partial state."
        )

        raise


    finally:
        conn.close()


if __name__ == "__main__":
    main()
