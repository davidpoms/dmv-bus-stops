from pathlib import Path


path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


old = """            LIMIT 1
            """
        ).fetchone()
"""


new = """            LIMIT 1
            """,
            (
                MIN_REVIEWERS,
            )
        ).fetchone()
"""


matches = text.count(old)

print(
    "Matches found:",
    matches
)


if matches != 2:
    raise Exception(
        f"Expected 2 matches, found {matches}"
    )


text = text.replace(
    old,
    new
)


path.write_text(text)

print(
    "✓ Fixed route and nearby MIN_REVIEWERS bindings"
)
