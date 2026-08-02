from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

# Replace old impact table
text = text.replace(
    "JOIN stop_improvement_impact sii",
    "LEFT JOIN improvement_recommendations sii"
)

text = text.replace(
    "sii.physical_stop_id",
    "sii.physical_stop_id"
)

# Replace old validation table
text = text.replace(
    "LEFT JOIN stop_validation sv",
    "LEFT JOIN stop_consensus sv"
)

# Replace old community action table
text = text.replace(
    "LEFT JOIN community_actions ca",
    "LEFT JOIN stop_consensus ca"
)

# Old columns from stop_improvement_impact
text = text.replace(
    "sii.opportunity_score",
    "0"
)

text = text.replace(
    "sii.priority_level",
    "sii.priority"
)

text = text.replace(
    "sii.priority_level IN ('high', 'very_high')",
    "sii.priority IN ('high', 'very_high')"
)

text = text.replace(
    "sv.status",
    "'needs_validation'"
)

text = text.replace(
    "ca.status",
    "'none'"
)

p.write_text(text)

print("Patched map_stops schema references")