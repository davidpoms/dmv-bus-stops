from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
/api/stops/${stopId}/evidence
"""

new = """
/stops/${stopId}
"""

if old not in text:
    raise Exception(
        "Could not find evidence endpoint"
    )

text = text.replace(
    old,
    new
)

p.write_text(text)

print(
    "Updated popup endpoint"
)
