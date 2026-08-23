from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """LEFT JOIN (
                SELECT
                    physical_stop_id,
                    'validated' AS status
                FROM stop_observations
                GROUP BY physical_stop_id
            ) sv
                ON ps.id = ca.stop_id
"""

text = text.replace(old, "")

p.write_text(text)

print("Removed obsolete stop_observations join")