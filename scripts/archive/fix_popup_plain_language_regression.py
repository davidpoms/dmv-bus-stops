from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


replacements = {
    "Improvement priority score: ${props.score}":
        "Community improvement priority: ${props.score}",

    "Score: ${props.score}":
        "Community improvement priority: ${props.score}",

    "Impact: ${props.impact}":
        ""
}


for old, new in replacements.items():

    if old in text:
        text = text.replace(
            old,
            new
        )


p.write_text(text)

print(
    "Updated popup plain language labels"
)
