from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()

old = '''
                            WMATA Data Availability:
                            ${
                                info.wmata.availability === "confirmed"
                                ? "Confirmed WMATA match"
                                : "No WMATA match available"
                            }
'''

new = '''
                            WMATA Data Availability:
                            <span class="${
                                info.wmata.availability === "confirmed"
                                ? "wmata-confirmed"
                                : "wmata-unavailable"
                            }">
                            ${
                                info.wmata.availability === "confirmed"
                                ? "Confirmed WMATA match"
                                : "No WMATA match available"
                            }
                            </span>
'''

if old not in text:
    raise Exception("WMATA availability block not found")

text = text.replace(old, new, 1)

path.write_text(text)

print("Added WMATA availability styling hooks")
