from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
SELECT COUNT(*)
FROM stop_consensus
WHERE stop_id IN ({})
AND consensus_status='verified'
"""

new = """
SELECT COUNT(*)
FROM stop_consensus
WHERE stop_id IN ({})
AND confidence IS NOT NULL
"""

if old not in text:
    raise Exception("Could not find consensus_status query block")

text = text.replace(old, new)

p.write_text(text)

print("Patched pipeline geography consensus query")