import sqlite3
import json

DB = "src/database/dmv_bus_stops.db"


def main():

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    rows = c.execute("""
        SELECT
            physical_stop_id,
            combined_route_weekday_boardings
        FROM opportunity_assessments
        ORDER BY combined_route_weekday_boardings ASC
    """).fetchall()


    total = len(rows)

    if total == 0:
        print("No opportunity assessments found")
        return


    updates = []


    for index, (physical_stop_id, exposure) in enumerate(rows):

        percentile = round(
            ((index + 1) / total) * 100
        )

        assessment = c.execute("""
            SELECT assessment_json
            FROM opportunity_assessments
            WHERE physical_stop_id = ?
        """,
        (physical_stop_id,)
        ).fetchone()


        data = {}

        if assessment and assessment[0]:

            try:
                data = json.loads(
                    assessment[0]
                )

            except Exception:
                data = {}


        data["rider_exposure_percentile"] = percentile


        updates.append(
            (
                json.dumps(data),
                physical_stop_id
            )
        )


    c.executemany("""
        UPDATE opportunity_assessments
        SET assessment_json = ?
        WHERE physical_stop_id = ?
    """,
    updates)


    conn.commit()

    print(
        f"Updated {total} stops with rider exposure percentiles"
    )


    conn.close()


if __name__ == "__main__":
    main()