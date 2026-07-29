import sqlite3

DB = "src/database/dmv_bus_stops.db"


def count_assignments(conn):
    return conn.execute(
        """
        SELECT COUNT(*)
        FROM stop_review_assignments
        """
    ).fetchone()[0]


def main():

    conn = sqlite3.connect(DB)

    before = count_assignments(conn)

    removed = conn.execute(
        """
        DELETE FROM stop_review_assignments
        WHERE status = 'assigned'
        AND completed_at IS NULL
        """
    ).rowcount

    conn.commit()

    after = count_assignments(conn)

    conn.close()

    print("Review assignment cleanup complete")
    print(f"Assignments before: {before}")
    print(f"Removed stale assignments: {removed}")
    print(f"Assignments after: {after}")


if __name__ == "__main__":
    main()
