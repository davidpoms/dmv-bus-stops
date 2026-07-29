from pathlib import Path

FILE = Path("src/dashboard/templates/review.html")

text = FILE.read_text()

old = """
<script src="/static/review_survey.js"></script>
<script src="/static/review_stop.js"></script>
"""

new = """
<script src="/static/review_info_loader.js"></script>
<script src="/static/review_survey.js"></script>
<script src="/static/review_stop.js"></script>
"""

if old not in text:
    raise Exception("Could not find script block")

text = text.replace(old, new)

FILE.write_text(text)

print("Added review_info_loader.js")
