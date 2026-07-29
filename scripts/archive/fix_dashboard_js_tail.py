from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

bad = "function loadPrioritySummary()ontentLoaded', function() {"

if bad in text:
    text = text.split(bad)[0]
    p.write_text(text)
    print("Removed corrupted duplicate JS tail")
else:
    print("Corruption marker not found")
