from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
            return {
                osm:
                    data.osm || {},

                observations:
                    data.observations || []

            };
"""


new = """
            return {

                osm:
                    data.evidence?.osm || {},

                observations:
                    data.evidence?.reviews || []

            };
"""


if old not in text:
    raise Exception(
        "Could not find evidence mapping block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Fixed evidence response mapping"
)
