from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """LEFT JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id"""

new = """JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id"""

count = text.count(old)

print("Found joins:", count)

if count == 0:
    raise Exception(
        "No matching improvement_opportunities joins found"
    )

text = text.replace(old, new)

path.write_text(text)

print("Updated map queries")