from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find("@app.route('/api/evidence-summary')")

if start == -1:
    start = text.find('@app.route("/api/evidence-summary")')

if start == -1:
    raise Exception("Could not find evidence-summary route")

end = text.find("\n@app.route", start + 10)

if end == -1:
    end = len(text)

section = text[start:end]

print("FOUND ROUTE:")
print(section)

old = '''summary["total"]'''

if old not in section:
    raise Exception("Could not find summary dictionary access")

section = section.replace(
    'summary["total"]',
    'summary[0] if isinstance(summary, tuple) else summary.get("total", 0)'
)

section = section.replace(
    'summary["wmata"]',
    'summary[1] if isinstance(summary, tuple) else summary.get("wmata", 0)'
)

section = section.replace(
    'summary["osm"]',
    'summary[2] if isinstance(summary, tuple) else summary.get("osm", 0)'
)

section = section.replace(
    'summary["reviews"]',
    'summary[3] if isinstance(summary, tuple) else summary.get("reviews", 0)'
)

text = text[:start] + section + text[end:]

path.write_text(text)

print("Fixed evidence summary tuple handling")
