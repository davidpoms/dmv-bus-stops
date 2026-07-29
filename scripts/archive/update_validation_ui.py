from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
            Status:
            ${stop.status}

            <br><br>

            <button onclick="submitValidation(${stop.stop_id}, 'validated')">
            Confirm
            </button>

            <button onclick="submitValidation(${stop.stop_id}, 'rejected')">
            Reject
            </button>
"""

new = """
            Status:
            ${stop.status}

            <br><br>

            <a href="${stop.streetview_url}" target="_blank"
            onclick="event.stopPropagation();">
            Open Street View
            </a>

            <br><br>

            <button onclick="event.stopPropagation(); submitValidation(${stop.stop_id}, 'validated')">
            Verified
            </button>

            <button onclick="event.stopPropagation(); submitValidation(${stop.stop_id}, 'rejected')">
            Incorrect
            </button>

            <button onclick="event.stopPropagation(); submitValidation(${stop.stop_id}, 'uncertain')">
            Unable to determine
            </button>
"""

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Updated validation workflow UI")
else:
    print("Validation UI block not found")
