from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()


old = """
def assign_stop(
    reviewer_id,
    scenario
):
"""


new = """
def assign_stop(
    reviewer_id,
    scenario,
    stop_id=None
):
"""


if old not in text:
    raise Exception(
        "Could not find assign_stop signature"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Updated assign_stop signature"
)
