from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )"""

new = """    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
        use_reloader=False
    )"""

if old not in text:
    print("Could not find expected app.run block.")
    raise SystemExit(1)

text = text.replace(old, new)

path.write_text(text)

print("Fixed Flask app.run debug settings.")
