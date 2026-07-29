from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def verification_coverage():
    return query(
        """
        SELECT

            COUNT(*) AS total_stops,

            SUM(
                CASE
                    WHEN id IN (
                        SELECT stop_id
                        FROM stop_reviews
                    )
                    THEN 1
                    ELSE 0
                END
            ) AS reviewed_stops,

            ROUND(
                100.0 *
                SUM(
                    CASE
                        WHEN id IN (
                            SELECT stop_id
                            FROM stop_reviews
                        )
                        THEN 1
                        ELSE 0
                    END
                ) / COUNT(*),
                1
            ) AS coverage_percent

        FROM physical_stops
        """
    )[0]

'''

if "def verification_coverage" not in text:
    p.write_text(text + addition)

print("Added verification coverage metric")
