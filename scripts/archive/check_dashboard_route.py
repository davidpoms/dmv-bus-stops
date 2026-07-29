from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find('@app.route("/dashboard")')

if start == -1:
    raise SystemExit("Dashboard route not found")

print(text[start:start+200])
