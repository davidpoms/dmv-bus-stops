from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                            fetch(`/stops/${props.stop_id}/amenities`)
                                .then(response => response.json())
"""

new = """
                            fetch(`/stops/${props.stop_id}/amenities`)
                                .then(response => {
                                    if (!response.ok) {
                                        return {
                                            wmata: null,
                                            osm: null
                                        };
                                    }

                                    return response.json();
                                })
"""

if old not in text:
    raise Exception("Amenity fetch block not found")

text = text.replace(old,new)

p.write_text(text)

print("Made amenity fetch resilient")
