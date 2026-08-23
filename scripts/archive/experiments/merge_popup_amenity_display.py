from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old_start = text.index(
"""
                                if (evidence.osm) {
"""
)

old_end = text.index(
"""
                                if (evidence.observations.length > 0) {
""",
old_start
)


new = """
                                if (
                                    evidence.osm ||
                                    detail.amenities?.wmata
                                ) {

                                    popup += `
                                    <br>
                                    <b>Existing stop information</b><br>
                                    `;


                                    if (detail.amenities?.wmata) {

                                        popup += `
                                        Shelter:
                                        ${
                                            detail.amenities.wmata.shelter === "1"
                                            ? "Yes"
                                            : "No"
                                        }
                                        (WMATA inventory)<br>

                                        Bench:
                                        ${
                                            detail.amenities.wmata.bench === "1"
                                            ? "Yes"
                                            : "No"
                                        }
                                        (WMATA inventory)<br>

                                        Accessible boarding:
                                        ${
                                            detail.amenities.wmata.accessible === "Y"
                                            ? "Yes"
                                            : "No"
                                        }<br>
                                        `;

                                    }


                                    if (evidence.osm) {

                                        popup += `
                                        Public mapping evidence:<br>

                                        Shelter mapped:
                                        ${
                                            evidence.osm.osm_shelter === 1
                                            ? "Yes"
                                            : "No"
                                        }<br>

                                        Bench mapped:
                                        ${
                                            evidence.osm.osm_bench === 1
                                            ? "Yes"
                                            : "No"
                                        }<br>
                                        `;

                                    }

                                }


"""

text = text[:old_start] + new + text[old_end:]


p.write_text(text)

print("Merged popup amenity sections")
