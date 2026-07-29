from pathlib import Path
import markdown


BASE_DIR = Path(__file__).resolve().parents[2]


def render_markdown_file(filename):

    path = BASE_DIR / "docs" / filename

    if not path.exists():
        return "<p>Documentation unavailable.</p>"

    text = path.read_text()

    return markdown.markdown(
        text,
        extensions=[
            "tables",
            "fenced_code"
        ]
    )
