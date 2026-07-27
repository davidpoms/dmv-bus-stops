from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
'''app = Flask(
    __name__,
    static_folder=None
)
''',
'''app = Flask(
    __name__,
    static_folder="../dashboard/static",
    static_url_path="/static",
    template_folder="../dashboard/templates"
)
'''
)

p.write_text(text)

print("Updated Flask static/template configuration")
