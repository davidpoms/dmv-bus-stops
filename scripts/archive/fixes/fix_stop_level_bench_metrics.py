from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

start = text.index("def stop_level_bench_metrics():")

# remove until end of file (function was appended last)
text = text[:start]

addition = r'''

def stop_level_bench_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                WHERE has_bench = 1
            ) AS community_confirmed_benches,

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                WHERE has_bench = 0
                AND bench_location_feasible = 1
            ) AS community_bench_opportunities,

            (
                SELECT COUNT(*)
                FROM physical_stops ps
                WHERE ps.id NOT IN (
                    SELECT DISTINCT stop_id
                    FROM stop_reviews
                )
            ) AS stops_needing_review

        """
    )[0]

'''

p.write_text(text + addition)

print("Fixed stop-level bench metrics")
