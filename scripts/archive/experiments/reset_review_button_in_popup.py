from pathlib import Path
import re

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


# Remove every popup block containing "Review this stop"
pattern = r"""
\s*popup \+= `

\s*<br><br>

\s*<a
\s*href="/review/start\?stop_id=\$\{props\.stop_id\}"
\s*class="stop-review-button">
\s*Review this stop
\s*</a>

\s*`;
"""

text, removed = re.subn(
    pattern,
    "",
    text,
    flags=re.VERBOSE
)


# Add one clean button before popup binding
marker = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


button = """
                                popup += `

                                <br><br>

                                <a
                                href="/review/start?stop_id=${props.stop_id}"
                                class="stop-review-button">
                                Review this stop
                                </a>

                                `;


                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


if marker not in text:
    raise Exception(
        "Could not find popup binding"
    )


text = text.replace(
    marker,
    button,
    1
)


p.write_text(text)

print(
    f"Removed {removed} duplicate review buttons and inserted one"
)
