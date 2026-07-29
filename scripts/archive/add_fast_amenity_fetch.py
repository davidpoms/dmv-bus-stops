from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                        fetch(
                            `/stops/${props.stop_id}`
                        )

                        .then(
                            response => response.json()
                        )

                        .then(
                            detail => {
"""

new = """
                        Promise.all([
                            fetch(`/stops/${props.stop_id}`)
                                .then(response => response.json()),

                            fetch(`/stops/${props.stop_id}/amenities`)
                                .then(response => response.json())
                        ])

                        .then(
                            ([detail, amenities]) => {

                                detail.amenities = amenities;
"""

if old not in text:
    raise Exception("Could not find stop fetch block")

text = text.replace(old,new)

p.write_text(text)

print("Added fast amenity fetch")
