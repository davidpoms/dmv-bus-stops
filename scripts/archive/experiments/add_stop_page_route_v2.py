from pathlib import Path

path = Path("src/api/app.py")
text = path.read_text(encoding="utf-8")

lines = text.splitlines()

# Exact route already present?
if any(line.strip() == '@app.route("/stop/<int:stop_id>")' for line in lines):
    print("HTML stop page route already exists.")
    raise SystemExit

marker = '@app.route("/stops/<int:stop_id>")'

if marker not in text:
    print("Could not find JSON /stops route.")
    raise SystemExit(1)

insert = '''
@app.route("/stop/<int:stop_id>")
def stop_page(stop_id):

    return render_template(
        "stop_detail.html",
        stop_id=stop_id
    )


'''

text = text.replace(marker, insert + marker, 1)

path.write_text(text, encoding="utf-8")

print("Inserted /stop/<stop_id> HTML route.")