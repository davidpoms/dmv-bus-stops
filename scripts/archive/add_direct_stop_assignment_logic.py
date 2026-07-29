from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()


old = """
    if scenario == "opportunity":
"""


new = """
    if stop_id:

        stop = (
            stop_id,
        )


    elif scenario == "opportunity":
"""


if old not in text:
    raise Exception(
        "Could not find scenario block"
    )


text = text.replace(
    old,
    new,
    1
)


p.write_text(text)

print(
    "Added direct stop assignment branch"
)
