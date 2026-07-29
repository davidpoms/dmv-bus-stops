from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
function loadEvidence(stopId) {

    return fetch(
        `/api/stops/${stopId}/evidence`
    )
    .then(
        response => response.json()
    );

}
"""


new = """
function loadEvidence(stopId) {

    return fetch(
        `/stops/${stopId}`
    )
    .then(
        response => {

            if(!response.ok){

                return {
                    osm: {},
                    observations: []
                };

            }

            return response.json();

        }
    )
    .then(
        data => {

            return {
                osm:
                    data.osm || {},

                observations:
                    data.observations || []

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


if old not in text:
    raise Exception(
        "Could not find loadEvidence function"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Fixed evidence loader"
)
