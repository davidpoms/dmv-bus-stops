from pathlib import Path

p = Path("src/reporting/export_priority_report.py")

text = p.read_text()

text = text.replace(
    """
            sr.notes
""",
    """
            so.notes
"""
)

text = text.replace(
    """
        LEFT JOIN stop_reviews sr

            ON io.physical_stop_id = sr.stop_id
""",
    """
        LEFT JOIN (

            SELECT
                physical_stop_id,
                GROUP_CONCAT(notes, '; ') AS notes

            FROM stop_observations

            GROUP BY physical_stop_id

        ) so

            ON io.physical_stop_id = so.physical_stop_id
"""
)

text = text.replace(
    """
            sr.notes
""",
    """
            so.notes
"""
)

text = text.replace(
    """
            sr.notes
""",
    """
            so.notes
"""
)

p.write_text(text)

print("Updated src/reporting/export_priority_report.py")
print("Replaced stop_reviews evidence join with stop_observations aggregation")
