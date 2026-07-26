import sqlite3

DB = "src/database/dmv_bus_stops.db"


def main():

    conn = sqlite3.connect(DB)

    before = conn.execute(
        """
        SELECT COUNT(*)
        FROM stop_review_assignments
        """
    ).fetchone()[0]


    removed = conn.execute(
        """
        DELETE FROM stop_review_assignments
        WHERE status='assigned'
        AND completed_at IS NULL
        """
    ).rowcount


    conn.commit()


    after = conn.execute(
        """
        SELECT COUNT(*)
        FROM stop_review_assignments
        """
    ).fetchone()[0]


    conn.close()


    print(f"Assignments before: {before}")
    print(f"Removed pending assignments: {removed}")
    print(f"Assignments after: {after}")


if __name__ == "__main__":
    main()
