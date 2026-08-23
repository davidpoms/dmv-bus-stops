from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()

old = '''
                            Match confidence:
                            ${
                                info.wmata.match_confidence || "Unknown"
                            }
'''

new = '''
                            Match quality:
                            ${
                                info.wmata.match_confidence === "high"
                                ? "High confidence match (within ~10 meters)"
                                : info.wmata.match_confidence === "medium"
                                ? "Medium confidence match (within ~50 meters)"
                                : info.wmata.match_confidence === "low"
                                ? "Low confidence match (verify location)"
                                : "Unknown"
                            }

                            <br>

                            Match distance:
                            ${
                                info.wmata.match_distance_m
                                ? Math.round(info.wmata.match_distance_m) + " meters"
                                : "Unknown"
                            }
'''

if old not in text:
    raise Exception("Could not find match confidence block")

text = text.replace(old, new, 1)

path.write_text(text)

print("Improved WMATA confidence display")
