from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = '''@app.route("/dashboard")
def dashboard():
    return send_from_directory(
        BASE_DIR / "src" / "dashboard" / "static",
        "dmv_bus_stops_dashboard.html"
    )
'''

new = '''@app.route("/dashboard")
def dashboard():
    return send_from_directory(
        BASE_DIR,
        "dmv_bus_stops_dashboard.html"
    )
'''

if old not in text:
    raise SystemExit("Dashboard route block not found")

text = text.replace(old, new)

path.write_text(text)

print("Fixed dashboard route")
