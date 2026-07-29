from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        WHERE sr.physical_stop_id = ?

        GROUP BY sr.physical_stop_id
"""

new = """
        WHERE sr.stop_id = ?

        GROUP BY sr.stop_id
"""

if old not in text:
    raise Exception("Could not find old stop_routes condition")

text = text.replace(old, new)

p.write_text(text)

print("Fixed stop_routes column reference")
