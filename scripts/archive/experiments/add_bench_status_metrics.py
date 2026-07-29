from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def bench_status_metrics():

    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM stop_observations
                WHERE bench_present = 'yes'
            ) AS confirmed_benches,


            (
                SELECT COUNT(*)
                FROM osm_features
                WHERE tags LIKE '%bench%'
            ) AS likely_osm_benches,


            (
                SELECT COUNT(*)
                FROM stop_observations
                WHERE bench_present = 'no'
                AND bench_feasible = 'yes'
            ) AS bench_candidates,


            (
                SELECT COUNT(*)
                FROM physical_stops p
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM stop_observations o
                    WHERE o.physical_stop_id = p.id
                )
            ) AS unknown_stops

        """
    )[0]

'''

if "def bench_status_metrics" not in text:
    text += addition
    print("Added bench status metrics")
else:
    print("Already exists")

p.write_text(text)
