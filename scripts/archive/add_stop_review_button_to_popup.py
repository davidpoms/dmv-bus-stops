from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


new = """
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


if old not in text:
    raise Exception(
        "Could not find popup binding block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Added stop review button to popup"
)
