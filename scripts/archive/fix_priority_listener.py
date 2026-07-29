from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
        loadStops(
            "",
            priority
        );
"""

new = """
        loadStops(
            "",
            "",
            priority
        );
"""

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Fixed priority listener arguments")
else:
    print("Listener block not found")
