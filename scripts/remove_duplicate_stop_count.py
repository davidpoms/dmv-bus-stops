from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

old = """
        STOP_COUNT=f"{query_count('SELECT COUNT(*) FROM physical_stops;'):,}",
"""

if old in text:
    text = text.replace(old, "", 1)
    print("Removed old STOP_COUNT injection")
else:
    print("Old STOP_COUNT line not found")

p.write_text(text)
