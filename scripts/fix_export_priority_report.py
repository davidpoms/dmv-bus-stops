from pathlib import Path

path = Path("src/reporting/export_priority_report.py")

text = path.read_text()

old = """
            GROUP_CONCAT(
                DISTINCT ir.recommendation_type
            ),
"""

new = """
            sii.recommendations,
"""

text = text.replace(old, new)

old = """
        LEFT JOIN improvement_recommendations ir

            ON io.physical_stop_id = ir.physical_stop_id
"""

text = text.replace(old, "")

path.write_text(text)

print("Updated export_priority_report.py")
