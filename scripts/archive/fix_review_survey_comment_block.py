from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()

old = """
        // disabled stopInfo overwrite
        /*
        container.innerHTML =
                    `
            <strong>${info.name || "Bus Stop"}</strong>
            <br>
            Stop ID: ${info.stop_id}
            <br>
            Coordinates:
            ${info.lat.toFixed(5)},
            ${info.lon.toFixed(5)}
            <br>
            Jurisdiction:
            ${geography}
            `;
"""

new = """
        // stopInfo rendering moved to review_info_loader.js
"""

if old not in text:
    raise Exception(
        "Could not find disabled stopInfo block"
    )

text = text.replace(
    old,
    new,
    1
)

p.write_text(text)

print(
    "Fixed review_survey.js comment block"
)
