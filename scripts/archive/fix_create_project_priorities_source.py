from pathlib import Path


path = Path(
    "src/assessment/create_project_priorities.py"
)

text = path.read_text()

old = """
        SELECT

            ir.physical_stop_id,

            ir.recommendation_type,

            ps.primary_name,

            io.opportunity_score,

            sii.priority_level,

            io.priority_rank

        FROM improvement_recommendations ir


        JOIN improvement_opportunities io

            ON ir.physical_stop_id = io.physical_stop_id


        JOIN stop_improvement_impact sii

            ON ir.physical_stop_id = sii.physical_stop_id


        JOIN physical_stops ps

            ON ir.physical_stop_id = ps.id


        ORDER BY

            io.opportunity_score DESC;
"""

new = """
        SELECT

            io.physical_stop_id,

            'improvement_opportunity',

            ps.primary_name,

            io.opportunity_score,

            COALESCE(
                sii.priority_level,
                'high'
            ),

            io.priority_rank

        FROM improvement_opportunities io


        LEFT JOIN stop_improvement_impact sii

            ON io.physical_stop_id = sii.physical_stop_id


        LEFT JOIN physical_stops ps

            ON io.physical_stop_id = ps.id


        WHERE io.opportunity_score >= 70


        ORDER BY

            io.opportunity_score DESC;
"""


if old not in text:
    raise SystemExit(
        "Expected query block not found"
    )


text = text.replace(
    old,
    new
)

path.write_text(text)

print(
    "Updated create_project_priorities source"
)
