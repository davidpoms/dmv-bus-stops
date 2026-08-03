from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


replacements = {
    "⭐ Highest Opportunity Stops":
        "⭐ Priority Verification Stops",

    "Review stops where available evidence suggests the greatest potential improvement.":
        "Review stops where additional community verification would provide the most value."
}


for old, new in replacements.items():

    if old not in text:
        raise Exception(f"Could not find: {old}")

    text = text.replace(
        old,
        new
    )


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated verification pathway language")