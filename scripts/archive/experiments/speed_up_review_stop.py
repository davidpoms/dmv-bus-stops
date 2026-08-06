from pathlib import Path

p = Path("src/dashboard/static/review_stop.js")

text = p.read_text()

old = """
            info.innerHTML = `
                <strong>${data.location}</strong>
                <br>
                Stop ID: ${data.stop_id}
                <br>
                Coordinates:
                ${data.lat.toFixed(5)},
                ${data.lon.toFixed(5)}

                <br>

                Camera heading:
                ${
                    data.heading
                    ? data.heading.toFixed(1)
                    : "unknown"
                }°

                <br><br>

                <a href="${data.streetview_url}"
                   target="_blank">
                   Open Street View
                </a>
            `;
"""

new = """
            const streetview =
                `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${data.lat},${data.lon}`;


            info.innerHTML = `
                <strong>${data.location}</strong>
                <br><br>

                Stop ID: ${data.stop_id}

                <br><br>

                Existing stop information:
                <br>
                Coordinates:
                ${data.lat.toFixed(5)},
                ${data.lon.toFixed(5)}

                <br><br>

                <a
                href="${streetview}"
                target="_blank"
                class="stop-review-button">
                Open Street View
                </a>
            `;
"""

if old not in text:
    raise Exception("Could not find review info block")

text = text.replace(old,new)

p.write_text(text)

print("Review Street View made instant")
