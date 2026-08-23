from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")

old = """
${
    result.reviewer_stats.first_review
    ?
    `
    <p>
    â
"""

new = """
${
    result.reviewer_stats.first_review
    ?
    `
    <p>
    ⭐ You completed the first review of this stop!
    </p>
    `
    :
    ""
}
"""

if old not in text:
    raise SystemExit("Broken first review block not found")

text = text.replace(old, new)

path.write_text(
    text,
    encoding="utf-8"
)

print("Fixed review completion first-review block")