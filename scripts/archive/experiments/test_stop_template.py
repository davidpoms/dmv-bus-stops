from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")

old = """@app.route("/stop/<int:stop_id>")
def stop_page(stop_id):

    return f"STOP PAGE WORKS: {stop_id}"
"""

new = """@app.route("/stop/<int:stop_id>")
def stop_page(stop_id):

    try:
        return render_template(
            "stop_detail.html",
            stop_id=stop_id
        )

    except Exception as e:
        return f"TEMPLATE ERROR: {type(e).__name__}: {e}", 500
"""

if old not in text:
    print("Could not find temporary stop route")
    raise SystemExit(1)

path.write_text(
    text.replace(old, new, 1),
    encoding="utf-8"
)

print("Restored stop template route with error capture")