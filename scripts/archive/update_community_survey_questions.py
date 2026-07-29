from pathlib import Path

path = Path("src/dashboard/static/survey.js")

text = path.read_text()

text = text.replace(
"""
Trash present:

<br>

<select id="trash">
<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unknown</option>
</select>
""",
""
)

text = text.replace(
"""
Trash present:
document.getElementById("trash").value,
""",
""
)

path.write_text(text)

print("Removed trash question from survey.js")
