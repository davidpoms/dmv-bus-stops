from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text(encoding="utf-8")


replacements = {
    "This stop has been identified as a possible opportunity for improvement. Community feedback will help determine whether riders would benefit from better waiting conditions.":
    "This stop has been prioritized for community verification because available information suggests additional review would be valuable. Community feedback will help confirm current waiting conditions and identify where improvements may be needed.",

    "Available records disagree about existing amenities at this stop. Public mapping suggests some waiting amenities may be present, while WMATA inventory does not show them. Your review will help confirm current conditions and whether additional improvements are needed.":
    "Available records disagree about existing amenities at this stop. Public mapping suggests some waiting amenities may be present, while WMATA inventory does not show them. Your review will help confirm current conditions and identify whether improvements may be needed.",

    "Community members have already provided feedback about this stop. Additional observations help confirm improvement needs.":
    "Community members have already provided feedback about this stop. Additional observations help improve confidence in the available information.",

    "Available records indicate this stop likely has a shelter. Your review will help determine whether additional improvements, such as seating, accessibility features, or other waiting area enhancements, would better support riders.":
    "Available records indicate this stop likely has a shelter. Your review will help confirm current conditions and identify whether additional waiting area improvements could better support riders."
}


for old, new in replacements.items():
    if old not in text:
        raise Exception(f"Missing text block:\n{old}")

    text = text.replace(old, new)


path.write_text(text, encoding="utf-8")

print("Updated dashboard verification language")