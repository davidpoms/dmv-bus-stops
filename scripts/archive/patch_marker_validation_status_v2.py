from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


# Replace priority color logic conditions
text = text.replace(
    'props.priority === "P1"',
    'props.validation_status === "validated"'
)

text = text.replace(
    'props.priority === "P2"',
    'props.validation_status === "needs_validation"'
)

text = text.replace(
    'props.priority === "P3"',
    'props.validation_status === "community_review"'
)


# Replace the old legend priority ordering behavior
text = text.replace(
"""
props.validation_status === "validated" ||
                    props.validation_status === "needs_validation"
""",
"""
props.validation_status === "validated"
"""
)


p.write_text(text)

print("marker validation conditions patched")

