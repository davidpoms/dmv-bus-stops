from pathlib import Path

path = Path("src/projects/create_improvement_projects.py")

text = path.read_text()

text = text.replace(
"""        SELECT

            physical_stop_id,

            recommendation_type

        FROM improvement_recommendations

        ORDER BY physical_stop_id;
""",
"""        SELECT

            physical_stop_id,

            recommendation_type

        FROM project_priorities

        ORDER BY priority_rank;
"""
)

path.write_text(text)

print("Updated create_improvement_projects.py")
