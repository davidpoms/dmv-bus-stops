from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
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
"""


new = """
                        SELECT
                            COALESCE(
                                SUM(unique_stops.daily_route_exposure),
                                0
                            )

                        FROM (

                            SELECT DISTINCT
                                sra.stop_id,
                                si.daily_route_exposure

                            FROM stop_review_assignments sra

                            LEFT JOIN stop_improvement_impact si

                            ON sra.stop_id =
                               si.physical_stop_id

                            WHERE sra.reviewer_id=?

                            AND sra.status='completed'

                        ) unique_stops
"""


if old not in text:
    raise Exception("impact query not found")


text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Fixed reviewer impact to unique stops")