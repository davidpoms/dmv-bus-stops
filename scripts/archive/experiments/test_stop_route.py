from pathlib import Path

path = Path("src/api/app.py")
text = path.read_text(encoding="utf-8")

old = """@app.route("/stop/<int:stop_id>")
def stop_page(stop_id):

    return render_template(
        "stop_detail.html",
        stop_id=stop_id
    )
"""

new = """@app.route("/stop/<int:stop_id>")
def stop_page(stop_id):

    return f"STOP PAGE WORKS: {stop_id}"
"""

if old not in text:
    print("Could not find stop_page() body exactly.")
    raise SystemExit(1)

path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Patched stop_page()")