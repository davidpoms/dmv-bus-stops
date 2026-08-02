from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """
LEFT JOIN stop_validation sv
    ON ps.id = sv.physical_stop_id
"""


new = """
LEFT JOIN (
    SELECT
        physical_stop_id,
        'validated' AS status
    FROM stop_observations
    GROUP BY physical_stop_id
) sv
    ON ps.id = sv.physical_stop_id
"""


count = text.count(old)

if count:
    text = text.replace(old, new)
    print(f"Replaced stop_validation joins: {count}")
else:
    print("No stop_validation join found")


path.write_text(text)

print("Finished patching review schema.")