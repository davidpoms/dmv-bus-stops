from pathlib import Path

p = Path("src/assessment/generate_improvement_recommendations.py")

text = p.read_text()

old = """
        SELECT

            sr.stop_id,

            sr.has_shelter,

            sr.has_bench,

            sr.bench_location_feasible,

            sr.concrete_pad_present,

            sr.curb_access_clear,

            sr.bus_ramp_access_clear,

            sr.landing_zone_clear,

            sr.notes,

            io.opportunity_score

        FROM stop_reviews sr

        LEFT JOIN improvement_opportunities io

            ON sr.stop_id = io.physical_stop_id;
"""

new = """
        SELECT

            o.physical_stop_id,

            CASE
                WHEN o.shelter_present IN ('yes','true','1')
                THEN 1
                ELSE 0
            END,

            CASE
                WHEN o.bench_present IN ('yes','true','1')
                THEN 1
                ELSE 0
            END,

            CASE
                WHEN o.bench_feasible IN ('yes','true','1')
                THEN 1
                ELSE 0
            END,

            NULL,

            CASE
                WHEN o.ada_clearance_possible IN ('yes','true','1')
                THEN 1
                ELSE 0
            END,

            CASE
                WHEN o.ada_clearance_possible IN ('yes','true','1')
                THEN 1
                ELSE 0
            END,

            CASE
                WHEN o.ada_clearance_possible IN ('yes','true','1')
                THEN 1
                ELSE 0
            END,

            o.notes,

            io.opportunity_score

        FROM stop_observations o

        LEFT JOIN improvement_opportunities io

            ON o.physical_stop_id = io.physical_stop_id;
"""

if old not in text:
    raise SystemExit("Expected recommendation query not found")

text = text.replace(old, new)

p.write_text(text)

print("Migrated recommendations to stop_observations")
