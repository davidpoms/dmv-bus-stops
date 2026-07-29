from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                <b>${stop.priority}</b>
                ${stop.location}

                <br>

                Score: ${stop.score}

                <br>

                Status:
                ${stop.status}

                <br><br>

                <a href="${stop.streetview_url}"
                   target="_blank"
                   onclick="event.stopPropagation();">
                   Open Street View
                </a>
"""


new = """
                <b>⭐ Help verify this stop</b>

                <br><br>

                ${stop.location}

                <br><br>

                <b>Why this matters:</b>

                <br>

                Transit improvement opportunity identified

                <br><br>

                <b>Community verification:</b>

                <br>

                Waiting for volunteer review

                <br><br>

                <a href="${stop.streetview_url}"
                   target="_blank"
                   onclick="event.stopPropagation();">
                   Open Street View Review
                </a>
"""


if old not in text:
    print("validation card block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


p.write_text(text)

print("validation queue cards patched")

