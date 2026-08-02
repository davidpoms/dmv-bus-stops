from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

# stop_consensus uses stop_id, not physical_stop_id
text = text.replace(
    "LEFT JOIN stop_consensus sv\n                ON ps.id = sv.physical_stop_id",
    "LEFT JOIN stop_consensus sv\n                ON ps.id = sv.stop_id"
)

text = text.replace(
    "LEFT JOIN stop_consensus ca\n                ON ps.id = ca.physical_stop_id",
    "LEFT JOIN stop_consensus ca\n                ON ps.id = ca.stop_id"
)

# remove references to old validation fields
text = text.replace(
    "sv.confidence",
    "sv.confidence"
)

# replace old status logic
text = text.replace(
    "sv.status",
    "CASE WHEN sv.id IS NOT NULL THEN 'validated' ELSE 'needs_validation' END"
)

# replace old action status
text = text.replace(
    "ca.status",
    "'none'"
)

p.write_text(text)

print("Patched stop_consensus joins")