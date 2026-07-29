from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

old = """
                    WHEN id IN (
                        SELECT stop_id
                        FROM stop_reviews
                    )
"""

new = """
                    WHEN id IN (
                        SELECT physical_stop_id
                        FROM stop_observations
                    )
"""

if old not in text:
    print("Target query not found")
else:
    text = text.replace(old, new)
    p.write_text(text)
    print("Fixed verification coverage query")
