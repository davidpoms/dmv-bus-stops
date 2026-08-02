from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = "AND consensus_status='verified'"

if old not in text:
    raise Exception("Could not find consensus_status text")

text = text.replace(
    old,
    "AND confidence IS NOT NULL"
)

p.write_text(text)

print("Patched consensus_status condition")