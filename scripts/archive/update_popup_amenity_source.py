from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                                if (
                                    evidence.wmata_evidence
                                ) {
"""

new = """
                                if (
                                    detail.amenities &&
                                    detail.amenities.wmata
                                ) {

                                    evidence.wmata_evidence =
                                        {
                                            wmata_shelter:
                                                String(detail.amenities.wmata.shelter),

                                            wmata_bench:
                                                String(detail.amenities.wmata.bench),

                                            wmata_accessible:
                                                detail.amenities.wmata.accessible,

                                            match_confidence:
                                                detail.amenities.wmata.confidence
                                        };

                                }


                                if (
                                    evidence.wmata_evidence
                                ) {
"""

if old not in text:
    raise Exception("Could not find WMATA block")

text=text.replace(old,new)

p.write_text(text)

print("Updated popup to use fast amenities")
