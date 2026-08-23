import sqlite3
import shutil
from pathlib import Path
from datetime import datetime


DB = Path("src/database/dmv_bus_stops.db")


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
            "stop_routes",
            "stop_routes_backup",
            "gtfs_stop_map",
            "routes",
            "bus_stops",
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
        # 2. Inspect current state
        # --------------------------------------------------

        current_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM stop_routes
            """
        ).fetchone()[0]

        print(
            "\nCurrent stop_routes rows:",
            current_rows
        )


        backup_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM stop_routes_backup
            """
        ).fetchone()[0]

        print(
            "stop_routes_backup rows:",
            backup_rows
        )


        gtfs_map_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM gtfs_stop_map
            """
        ).fetchone()[0]

        print(
            "gtfs_stop_map rows:",
            gtfs_map_rows
        )


        # --------------------------------------------------
        # 3. Calculate expected rebuild BEFORE changing DB
        # --------------------------------------------------

        expected_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT
                    gm.bus_stop_id,
                    r.id AS route_id

                FROM stop_routes_backup sr

                JOIN gtfs_stop_map gm
                    ON CAST(sr.stop_id AS TEXT)
                       = gm.gtfs_stop_id

                JOIN routes r
                    ON r.route_id = sr.route_id
            )
            """
        ).fetchone()[0]


        expected_stops = conn.execute(
            """
            SELECT COUNT(DISTINCT gm.bus_stop_id)
            FROM stop_routes_backup sr

            JOIN gtfs_stop_map gm
                ON CAST(sr.stop_id AS TEXT)
                   = gm.gtfs_stop_id

            JOIN routes r
                ON r.route_id = sr.route_id
            """
        ).fetchone()[0]


        expected_routes = conn.execute(
            """
            SELECT COUNT(DISTINCT r.id)
            FROM stop_routes_backup sr

            JOIN gtfs_stop_map gm
                ON CAST(sr.stop_id AS TEXT)
                   = gm.gtfs_stop_id

            JOIN routes r
                ON r.route_id = sr.route_id
            """
        ).fetchone()[0]


        print("\nExpected rebuilt rows:", expected_rows)
        print("Expected distinct stops:", expected_stops)
        print("Expected distinct routes:", expected_routes)


        # --------------------------------------------------
        # 4. Check for unmapped backup stops
        # --------------------------------------------------

        unmapped_stops = conn.execute(
            """
            SELECT COUNT(DISTINCT sr.stop_id)

            FROM stop_routes_backup sr

            LEFT JOIN gtfs_stop_map gm
                ON CAST(sr.stop_id AS TEXT)
                   = gm.gtfs_stop_id

            WHERE gm.gtfs_stop_id IS NULL
            """
        ).fetchone()[0]


        print(
            "Backup stops without GTFS map:",
            unmapped_stops
        )


        # --------------------------------------------------
        # 5. Check for route codes missing from routes
        # --------------------------------------------------

        unmapped_routes = conn.execute(
            """
            SELECT COUNT(DISTINCT sr.route_id)

            FROM stop_routes_backup sr

            LEFT JOIN routes r
                ON r.route_id = sr.route_id

            WHERE r.id IS NULL
            """
        ).fetchone()[0]


        print(
            "Backup route codes missing from routes:",
            unmapped_routes
        )


        # --------------------------------------------------
        # 6. Safety checks BEFORE destructive operation
        # --------------------------------------------------

        if expected_rows == 0:
            raise RuntimeError(
                "Expected rebuilt row count is ZERO. "
                "Aborting without changing stop_routes."
            )


        if expected_rows < 1000:
            raise RuntimeError(
                f"Expected rebuilt row count is suspiciously "
                f"low ({expected_rows}). "
                "Aborting without changing stop_routes."
            )


        if expected_stops < 1000:
            raise RuntimeError(
                f"Expected distinct stop count is suspiciously "
                f"low ({expected_stops}). "
                "Aborting without changing stop_routes."
            )


        # --------------------------------------------------
        # 7. Create database backup
        # --------------------------------------------------

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_path = DB.with_name(
            f"{DB.stem}_before_stop_routes_rebuild_"
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
        # 8. Rebuild transactionally
        # --------------------------------------------------

        print("\nBeginning rebuild...")

        conn.execute("BEGIN")

        conn.execute(
            """
            DELETE FROM stop_routes
            """
        )

        conn.execute(
            """
            INSERT INTO stop_routes
            (
                stop_id,
                route_id
            )

            SELECT DISTINCT
                gm.bus_stop_id,
                r.id

            FROM stop_routes_backup sr

            JOIN gtfs_stop_map gm
                ON CAST(sr.stop_id AS TEXT)
                   = gm.gtfs_stop_id

            JOIN routes r
                ON r.route_id = sr.route_id
            """
        )


        # --------------------------------------------------
        # 9. Validate rebuilt table INSIDE transaction
        # --------------------------------------------------

        actual_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM stop_routes
            """
        ).fetchone()[0]


        actual_stops = conn.execute(
            """
            SELECT COUNT(DISTINCT stop_id)
            FROM stop_routes
            """
        ).fetchone()[0]


        print("\nValidation:")
        print(
            "Actual rows:",
            actual_rows
        )

        print(
            "Actual distinct stops:",
            actual_stops
        )


        if actual_rows != expected_rows:
            raise RuntimeError(
                "Row-count validation failed: "
                f"expected {expected_rows}, "
                f"got {actual_rows}"
            )


        if actual_stops != expected_stops:
            raise RuntimeError(
                "Distinct-stop validation failed: "
                f"expected {expected_stops}, "
                f"got {actual_stops}"
            )


        # --------------------------------------------------
        # 10. Validate foreign-key-like relationships
        # --------------------------------------------------

        orphan_route_links = conn.execute(
            """
            SELECT COUNT(*)

            FROM stop_routes sr

            LEFT JOIN routes r
                ON sr.route_id = r.id

            WHERE r.id IS NULL
            """
        ).fetchone()[0]


        orphan_stop_links = conn.execute(
            """
            SELECT COUNT(*)

            FROM stop_routes sr

            LEFT JOIN bus_stops bs
                ON sr.stop_id = bs.id

            WHERE bs.id IS NULL
            """
        ).fetchone()[0]


        print(
            "Orphan route links:",
            orphan_route_links
        )

        print(
            "Orphan stop links:",
            orphan_stop_links
        )


        if orphan_route_links != 0:
            raise RuntimeError(
                "Validation failed: orphan route links found."
            )


        if orphan_stop_links != 0:
            raise RuntimeError(
                "Validation failed: orphan bus-stop links found."
            )


        # --------------------------------------------------
        # 11. Compare against the expected exact dataset
        # --------------------------------------------------

        missing_expected = conn.execute(
            """
            SELECT COUNT(*)

            FROM (
                SELECT DISTINCT
                    gm.bus_stop_id AS stop_id,
                    r.id AS route_id

                FROM stop_routes_backup sr

                JOIN gtfs_stop_map gm
                    ON CAST(sr.stop_id AS TEXT)
                       = gm.gtfs_stop_id

                JOIN routes r
                    ON r.route_id = sr.route_id
            ) expected

            LEFT JOIN stop_routes actual
                ON actual.stop_id = expected.stop_id
                AND actual.route_id = expected.route_id

            WHERE actual.id IS NULL
            """
        ).fetchone()[0]


        unexpected_rows = conn.execute(
            """
            SELECT COUNT(*)

            FROM stop_routes actual

            LEFT JOIN (
                SELECT DISTINCT
                    gm.bus_stop_id AS stop_id,
                    r.id AS route_id

                FROM stop_routes_backup sr

                JOIN gtfs_stop_map gm
                    ON CAST(sr.stop_id AS TEXT)
                       = gm.gtfs_stop_id

                JOIN routes r
                    ON r.route_id = sr.route_id
            ) expected

                ON expected.stop_id = actual.stop_id
                AND expected.route_id = actual.route_id

            WHERE expected.stop_id IS NULL
            """
        ).fetchone()[0]


        print(
            "Expected links missing:",
            missing_expected
        )

        print(
            "Unexpected links:",
            unexpected_rows
        )


        if missing_expected != 0:
            raise RuntimeError(
                "Validation failed: expected route links "
                "are missing."
            )


        if unexpected_rows != 0:
            raise RuntimeError(
                "Validation failed: unexpected route links "
                "were created."
            )


        # --------------------------------------------------
        # 12. Everything passed
        # --------------------------------------------------

        conn.commit()

        print("\n===================================")
        print("STOP ROUTES REBUILD SUCCESSFUL")
        print("===================================")

        print(
            "stop_routes rows:",
            actual_rows
        )

        print(
            "distinct stops:",
            actual_stops
        )

        print(
            "backup stops without GTFS map:",
            unmapped_stops
        )

        print(
            "route codes without routes entry:",
            unmapped_routes
        )

        print(
            "database backup:",
            backup_path
        )

        print("\nNo validation errors.")


    except Exception:

        print(
            "\nERROR: rebuild failed."
        )

        print(
            "Rolling back transaction..."
        )

        conn.rollback()

        print(
            "stop_routes was NOT left in the partially rebuilt state."
        )

        raise


    finally:
        conn.close()


if __name__ == "__main__":
    main()
