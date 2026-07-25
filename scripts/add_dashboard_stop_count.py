from pathlib import Path

path = Path("src/dashboard/generate_dashboard.py")

text = path.read_text()

old = """    html = template.substitute("""
new = """    html = template.substitute(
        STOP_COUNT=f"{query_count('SELECT COUNT(*) FROM physical_stops;'):,}","""

if old not in text:
    raise SystemExit("Could not find template substitution block")

text = text.replace(old, new)

insert = """
def query_count(sql):
    import sqlite3

    db = BASE_DIR / "src/database/dmv_bus_stops.db"

    conn = sqlite3.connect(db)
    count = conn.execute(sql).fetchone()[0]
    conn.close()

    return count

"""

marker = "def generate_dashboard():"

text = text.replace(marker, insert + marker)

path.write_text(text)

print("Added dashboard stop count injection")
