from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """app = Flask(
    __name__,
    static_folder=None
)
"""

new = """app = Flask(
    __name__,
    static_folder=None,
    template_folder="../dashboard/templates"
)
"""

if old not in text:
    raise SystemExit("Could not find Flask initialization block")

text = text.replace(old, new)

path.write_text(text)

print("Updated Flask template folder")
