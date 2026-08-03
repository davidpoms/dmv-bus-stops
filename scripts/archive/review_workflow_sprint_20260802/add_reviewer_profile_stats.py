from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = '''
            "stops_reviewed":
                query_db(
                    """
                    SELECT COUNT(DISTINCT stop_id)
                    FROM stop_review_assignments
                    WHERE reviewer_id=?
                    AND status='completed'
                    """,
                    (reviewer_id,)
                )[0][0]

        },
'''


new = '''
            "stops_reviewed":
                query_db(
                    """
                    SELECT COUNT(DISTINCT stop_id)
                    FROM stop_review_assignments
                    WHERE reviewer_id=?
                    AND status='completed'
                    """,
                    (reviewer_id,)
                )[0][0],

            "total_rider_impact":
                round(
                    query_db(
                        """
                        SELECT
                            COALESCE(
                                SUM(si.daily_route_exposure),
                                0
                            )

                        FROM stop_review_assignments sra

                        LEFT JOIN stop_improvement_impact si
                        ON sra.stop_id = si.physical_stop_id

                        WHERE sra.reviewer_id=?

                        AND sra.status='completed'
                        """,
                        (reviewer_id,)
                    )[0][0]
                ),

            "routes_covered":
                (
                    query_db(
                        """
                        SELECT
                            GROUP_CONCAT(
                                DISTINCT r.route_id
                            )

                        FROM stop_review_assignments sra

                        JOIN physical_stop_members psm
                        ON sra.stop_id =
                           psm.physical_stop_id

                        JOIN stop_routes sr
                        ON psm.bus_stop_id =
                           sr.stop_id

                        JOIN routes r
                        ON sr.route_id =
                           r.route_id

                        WHERE sra.reviewer_id=?

                        AND sra.status='completed'
                        """,
                        (reviewer_id,)
                    )[0][0].split(",")
                    if query_db(
                        """
                        SELECT
                            GROUP_CONCAT(
                                DISTINCT r.route_id
                            )

                        FROM stop_review_assignments sra

                        JOIN physical_stop_members psm
                        ON sra.stop_id =
                           psm.physical_stop_id

                        JOIN stop_routes sr
                        ON psm.bus_stop_id =
                           sr.stop_id

                        JOIN routes r
                        ON sr.route_id =
                           r.route_id

                        WHERE sra.reviewer_id=?

                        AND sra.status='completed'
                        """,
                        (reviewer_id,)
                    )[0][0]
                    else []
                )

        },
'''


if old not in text:
    raise Exception("Reviewer stats block not found")


text = text.replace(old,new)

path.write_text(
    text,
    encoding="utf-8"
)

print("Added reviewer profile stats")