from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """(
                route,
                impact,
                impact,
                impact,
                impact
            )"""

new = """(
                route,
                impact,
                impact,
                impact
            )"""

if old not in text:
    raise SystemExit("Parameter block not found")

text = text.replace(old, new, 1)

p.write_text(text)

print("Fixed impact parameter count")
