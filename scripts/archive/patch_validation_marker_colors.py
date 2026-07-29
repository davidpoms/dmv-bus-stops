from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


text = text.replace(
    'color: "red"',
    'color: "green"'
)

text = text.replace(
    'color: "orange"',
    'color: "gray"'
)

text = text.replace(
    'color: "gold"',
    'color: "orange"'
)


p.write_text(text)

print("validation marker colors patched")

