from pathlib import Path

p = Path("scripts/build_stop_consensus.py")

text = p.read_text()

marker = """
cur = conn.cursor()
"""

insert = """
cur = conn.cursor()

# Clear stale consensus records before rebuilding
cur.execute(
    \"\"\"
    DELETE FROM stop_consensus
    \"\"\"
)
"""

if "DELETE FROM stop_consensus" in text:
    print("Cleanup already present.")
    raise SystemExit

if marker not in text:
    print("Cursor marker not found.")
    raise SystemExit

text = text.replace(
    marker,
    insert
)

p.write_text(text)

print("Added consensus cleanup step.")
