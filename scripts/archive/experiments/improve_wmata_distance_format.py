from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()

old = '''
                                info.wmata.match_distance_m
                                ? Math.round(info.wmata.match_distance_m) + " meters"
                                : "Unknown"
'''

new = '''
                                info.wmata.match_distance_m !== null
                                ? (
                                    info.wmata.match_distance_m < 10
                                    ? info.wmata.match_distance_m.toFixed(1)
                                    : Math.round(info.wmata.match_distance_m)
                                ) + " meters"
                                : "Unknown"
'''

if old not in text:
    raise Exception("Distance display block not found")

text = text.replace(old, new, 1)

path.write_text(text)

print("Improved WMATA distance formatting")
