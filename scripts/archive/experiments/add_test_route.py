from pathlib import Path

app_path = Path("src/api/app.py")

text = app_path.read_text(encoding="utf-8")

if '@app.route("/test-route")' in text:
    print("Test route already exists")
    raise SystemExit()

marker = 'if __name__ == "__main__":'

if marker not in text:
    print("Could not find __main__ block")
    raise SystemExit(1)

route = '''

@app.route("/test-route")
def test_route():
    return "hello"

'''

text = text.replace(marker, route + "\n" + marker, 1)

app_path.write_text(text, encoding="utf-8")

print("Added test route")