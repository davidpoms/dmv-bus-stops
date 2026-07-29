from pathlib import Path

path = Path("src/dashboard/generate_dashboard.py")

text = path.read_text()

old = """
    status_list = "\\n".join(
        f"<li>{status}: {count}</li>"
        for status, count in data["project_status"].items()
    )
"""

if old not in text:
    raise SystemExit("status_list block not found")

text = text.replace(old, "")

text = text.replace(
    "        status_list=status_list,\n",
    ""
)

path.write_text(text)

print("Removed old project status generator")
