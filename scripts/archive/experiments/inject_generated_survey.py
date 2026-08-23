from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text()

start = text.index("<h3>Review mode</h3>")
end = text.index("<br><br>\n\n\n<button type=\"submit\">")

replacement = """
{{ survey_html|safe }}
"""

text = text[:start] + replacement + text[end:]

path.write_text(text)

print("Injected generated survey")
