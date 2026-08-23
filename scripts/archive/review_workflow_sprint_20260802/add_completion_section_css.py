from pathlib import Path

path = Path("src/dashboard/static/dashboard.css")

text = path.read_text(encoding="utf-8")

addition = """

.impact-section {
    margin-top: 24px;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #ddd;
}

.impact-section h2 {
    margin-top: 0;
}

.current-review {
    margin-top: 20px;
}

"""

if ".impact-section {" not in text:
    text += addition

path.write_text(text, encoding="utf-8")

print("Added completion section styling")