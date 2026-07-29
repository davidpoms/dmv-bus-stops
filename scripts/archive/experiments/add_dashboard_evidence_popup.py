from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                        .then(
                            detail => {

                                let popup = `
"""

new = """
                        .then(
                            detail => {

                                return loadEvidence(props.stop_id)
                                .then(
                                    evidence => {

                                let popup = `
"""

if old not in text:
    raise SystemExit("Could not find popup insertion point")


text = text.replace(old, new, 1)


old2 = """
                                if (detail.confidence) {
"""

new2 = """
                                if (evidence.osm) {

                                    popup += `
                                    <br>
                                    <b>OSM Evidence</b><br>

                                    Bus stop mapped:
                                    ${evidence.osm.osm_bus_stop === 1 ? "Yes" : "No"}<br>

                                    Shelter:
                                    ${evidence.osm.osm_shelter === 1 ? "Yes" : "No"}<br>

                                    Bench:
                                    ${evidence.osm.osm_bench === 1 ? "Yes" : "No"}<br>
                                    `;

                                }


                                if (evidence.observations.length > 0) {

                                    popup += `
                                    <br>
                                    <b>Field Observations</b><br>
                                    `;


                                    evidence.observations.forEach(
                                        obs => {

                                            popup += `
                                            Reviewer:
                                            ${obs.observer || "Unknown"}<br>

                                            Bench:
                                            ${obs.bench_present}<br>

                                            Feasible:
                                            ${obs.bench_feasible}<br>

                                            Confidence:
                                            ${obs.confidence}<br>

                                            Notes:
                                            ${obs.notes || ""}<br><br>
                                            `;

                                        }
                                    );

                                }


                                if (detail.confidence) {
"""

if old2 not in text:
    raise SystemExit("Could not find evidence insertion location")


text = text.replace(old2, new2, 1)


old3 = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();

                            }
                        );
"""

new3 = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();

                                    }
                                );

                            }
                        );
"""

if old3 not in text:
    raise SystemExit("Could not find popup closing block")


text = text.replace(old3, new3, 1)


p.write_text(text)

print("Added evidence data to dashboard popup")
