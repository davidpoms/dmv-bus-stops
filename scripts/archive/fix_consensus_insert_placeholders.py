from pathlib import Path

p = Path("scripts/build_stop_consensus.py")

text = p.read_text()

old = """
        VALUES (?, ?, ?, ?, ?, ?, ?)
"""

new = """
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

if old not in text:
    print("INSERT placeholder pattern not found")
    raise SystemExit

text = text.replace(old,new)

p.write_text(text)

print("Fixed consensus INSERT placeholders")
