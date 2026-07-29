from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
            <div class="priorityItem">

            <b>${stop.priority}</b>
            ${stop.location}
"""

new = """
            <div class="priorityItem"
            onclick="focusValidationStop(${stop.stop_id})"
            style="cursor:pointer;">

            <b>${stop.priority}</b>
            ${stop.location}
"""

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Added validation queue click handler")
else:
    print("Queue item block not found")
