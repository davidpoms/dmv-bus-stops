from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

# Undo incorrect ca column replacements
text = text.replace(
    "ca.physical_stop_id",
    "ca.stop_id"
)

# Restore the actual consensus table joins
text = text.replace(
    "LEFT JOIN (SELECT physical_stop_id, 'none' AS status FROM stop_observations GROUP BY physical_stop_id) ca",
    "LEFT JOIN stop_consensus ca"
)

path.write_text(text)

print("Fixed ca alias references.")