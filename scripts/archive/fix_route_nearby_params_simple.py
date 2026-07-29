from pathlib import Path

path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


old = '''            LIMIT 1
            """
        ).fetchone()'''


new = '''            LIMIT 1
            """,
            (
                MIN_REVIEWERS,
            )
        ).fetchone()'''


count = text.count(old)

print(
    "Matching blocks found:",
    count
)


if count != 2:
    raise Exception(
        f"Expected 2 blocks, found {count}"
    )


text = text.replace(
    old,
    new
)


path.write_text(text)

print(
    "✓ Added MIN_REVIEWERS params to route and nearby queries"
)
