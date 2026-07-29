from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def bench_priority_metrics():

    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM stop_osm_evidence
                WHERE osm_bench = 1
            ) AS confirmed_benches,


            (
                SELECT COUNT(*)
                FROM stop_osm_evidence
                WHERE osm_shelter = 1
                AND osm_bench = 0
            ) AS shelter_without_bench,


            (
                SELECT COUNT(*)
                FROM stop_osm_evidence
                WHERE osm_bus_stop = 1
                AND osm_bench = 0
                AND osm_shelter = 0
            ) AS high_priority_reviews

        """
    )[0]

'''

if "def bench_priority_metrics" not in text:
    text += addition

p.write_text(text)

print("Added bench priority metrics")
