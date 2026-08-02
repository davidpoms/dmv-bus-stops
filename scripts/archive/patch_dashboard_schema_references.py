from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

# Replace old validation table logic
text = text.replace(
    "LEFT JOIN stop_validation sv",
    "LEFT JOIN (SELECT physical_stop_id, 'validated' AS status FROM stop_observations GROUP BY physical_stop_id) sv"
)

# Remove old community action table references
text = text.replace(
    "LEFT JOIN community_actions ca",
    "LEFT JOIN (SELECT physical_stop_id, 'none' AS status FROM stop_observations GROUP BY physical_stop_id) ca"
)

text = text.replace(
    "FROM community_actions",
    "FROM stop_observations"
)

# Old confidence column -> status
text = text.replace(
    "sv.confidence",
    "sv.status"
)

# Old stop_id joins from old tables
text = text.replace(
    "ca.stop_id",
    "ca.physical_stop_id"
)

text = text.replace(
    "sv.stop_id",
    "sv.physical_stop_id"
)

path.write_text(text)

print("Patched dashboard schema references.")