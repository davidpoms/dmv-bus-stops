from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

old = """
        CONSENSUS_STOPS=f"{metrics['verification']['consensus_stops']:,}",
"""

new = """
        CONSENSUS_STOPS=f"{metrics['verification']['consensus_stops'] or 0:,}",
"""

if old not in text:
    raise SystemExit("Could not find CONSENSUS_STOPS line")

text = text.replace(old, new)

p.write_text(text)

print("Fixed consensus dashboard formatting")
