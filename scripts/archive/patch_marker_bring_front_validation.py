from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                    props.validation_status === "validated" ||
                    props.validation_status === "needs_validation"
"""


new = """
                    props.validation_status === "validated"
"""


if old not in text:
    print("bring front block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


p.write_text(text)

print("marker bring-to-front validation patched")

