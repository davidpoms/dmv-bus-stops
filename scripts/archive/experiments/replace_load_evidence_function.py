from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


start = text.find("function loadEvidence(stopId)")

if start == -1:
    raise Exception(
        "Could not find loadEvidence function"
    )


end = text.find(
    "\n}\n\n\nfunction loadStops",
    start
)

if end == -1:
    raise Exception(
        "Could not find end of loadEvidence function"
    )

end += 2


replacement = """
function loadEvidence(stopId) {

    return fetch(
        `/stops/${stopId}`
    )
    .then(
        response => {

            if(!response.ok){

                return {
                    evidence: {}
                };

            }

            return response.json();

        }
    )
    .then(
        data => {

            return {
                osm:
                    data.evidence?.osm || {},

                observations:
                    data.evidence?.reviews || []

            };

        }
    )
    .catch(
        error => {

            console.warn(
                "Evidence unavailable:",
                error
            );

            return {
                osm: {},
                observations: []
            };

        }
    );

}
"""


text = (
    text[:start]
    +
    replacement
    +
    text[end:]
)


p.write_text(text)

print(
    "Replaced loadEvidence function"
)
