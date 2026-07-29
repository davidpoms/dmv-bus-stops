from pathlib import Path


path = Path(
    "src/review/assignment_router.py"
)

lines = path.read_text().splitlines()


new_lines = []

inside_route = False
inside_nearby = False
fixed_route = False
fixed_nearby = False


for line in lines:

    if 'elif scenario == "route"' in line:
        inside_route = True

    if 'elif scenario == "nearby"' in line:
        inside_nearby = True

    # Add missing params after route LIMIT block
    if (
        inside_route
        and not fixed_route
        and line.strip() == '"""\n'.strip()
    ):
        new_lines.append(line)
        continue


    new_lines.append(line)


# second pass: safer direct replacement of the exact bad pattern
text = "\n".join(lines)


bad = """            LIMIT 1
            """
        ).fetchone()"""


good = """            LIMIT 1
            """,
            (
                MIN_REVIEWERS,
            )
        ).fetchone()"""


count = text.count(bad)

print("Bad blocks found:", count)


if count:
    text = text.replace(
        bad,
        good
    )

    path.write_text(text)

print(
    "✓ Fixed assignment router consensus bindings"
)
