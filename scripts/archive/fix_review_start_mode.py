from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    scenario = request.args.get(
        "scenario",
        "opportunity"
    )
"""

new = """
    scenario = request.args.get(
        "mode",
        request.args.get(
            "scenario",
            "opportunity"
        )
    )
"""

if old not in text:
    raise Exception("Could not find scenario block")


text = text.replace(
    old,
    new
)

p.write_text(text)

print("Review start now accepts mode")
