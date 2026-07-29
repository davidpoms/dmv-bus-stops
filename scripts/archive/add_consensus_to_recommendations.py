from pathlib import Path

p = Path("src/assessment/generate_improvement_recommendations.py")

text = p.read_text()


old = """
            COALESCE(ste.gtfs_bus_stop,0)


        FROM improvement_opportunities io
"""

new = """
            COALESCE(ste.gtfs_bus_stop,0),

            COALESCE(sc.has_bench, NULL),

            COALESCE(sc.has_shelter, NULL),

            COALESCE(sc.ada_accessible, NULL),

            COALESCE(sc.confidence,0)


        FROM improvement_opportunities io
"""


if old not in text:
    print("SQL insertion point not found")
    raise SystemExit


text = text.replace(old,new)


old2 = """
        LEFT JOIN stop_transit_evidence ste

            ON ste.stop_id = io.physical_stop_id

        ORDER BY io.opportunity_score DESC;
"""


new2 = """
        LEFT JOIN stop_transit_evidence ste

            ON ste.stop_id = io.physical_stop_id

        LEFT JOIN stop_consensus sc

            ON sc.stop_id = io.physical_stop_id

        ORDER BY io.opportunity_score DESC;
"""


if old2 not in text:
    print("JOIN insertion point not found")
    raise SystemExit


text=text.replace(old2,new2)


old3 = """
            gtfs_bus_stop
        ) = row
"""


new3 = """
            gtfs_bus_stop,

            consensus_bench,

            consensus_shelter,

            consensus_ada,

            consensus_confidence

        ) = row
"""


if old3 not in text:
    print("Tuple insertion point not found")
    raise SystemExit


text=text.replace(old3,new3)


p.write_text(text)

print("Consensus fields added")
