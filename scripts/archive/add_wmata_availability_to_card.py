from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()

old = '''
                            WMATA Stop ID:
                            ${info.wmata.stop_id || "Unknown"}

                            <br>

                            Status:
'''

new = '''
                            WMATA Data Availability:
                            ${
                                info.wmata.availability === "confirmed"
                                ? "Confirmed WMATA match"
                                : "No WMATA match available"
                            }

                            <br><br>

                            WMATA Stop ID:
                            ${info.wmata.stop_id || "Unknown"}

                            <br>

                            Status:
'''

if old not in text:
    raise Exception("Could not find WMATA Stop ID section")

text = text.replace(old, new, 1)

path.write_text(text)

print("Added WMATA availability display")
