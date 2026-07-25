from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def stop_level_bench_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM stop_reviews
                WHERE has_bench = 1
            ) AS community_confirmed_benches,

            (
                SELECT COUNT(*)
                FROM stop_reviews
                WHERE has_bench = 0
                AND bench_location_feasible = 1
            ) AS community_bench_opportunities

        """
    )[0]

'''

if "def stop_level_bench_metrics" not in text:
    p.write_text(text + addition)

print("Added stop level bench metrics")
