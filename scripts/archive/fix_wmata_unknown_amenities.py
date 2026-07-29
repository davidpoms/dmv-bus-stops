from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()

old_shelter = '''
                            ${
                                info.wmata.shelter === "1"
                                ? "Yes"
                                : "No"
                            }
'''

new_shelter = '''
                            ${
                                info.wmata.shelter === "1"
                                ? "Yes"
                                : info.wmata.shelter === "0"
                                ? "No"
                                : "Unknown"
                            }
'''

old_bench = '''
                            ${
                                info.wmata.bench === "1"
                                ? "Yes"
                                : "No"
                            }
'''

new_bench = '''
                            ${
                                info.wmata.bench === "1"
                                ? "Yes"
                                : info.wmata.bench === "0"
                                ? "No"
                                : "Unknown"
                            }
'''

if old_shelter not in text:
    raise Exception("Shelter block not found")

if old_bench not in text:
    raise Exception("Bench block not found")

text = text.replace(old_shelter, new_shelter, 1)
text = text.replace(old_bench, new_bench, 1)

path.write_text(text)

print("Fixed WMATA unknown amenity display")
