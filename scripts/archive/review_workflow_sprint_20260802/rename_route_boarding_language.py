from pathlib import Path

# Update backend API naming
app = Path("src/api/app.py")

text = app.read_text(encoding="utf-8")

text = text.replace(
    '"total_rider_impact"',
    '"total_route_boardings_represented"'
)

app.write_text(
    text,
    encoding="utf-8"
)


# Update frontend wording
review = Path("src/dashboard/templates/review.html")

text = review.read_text(encoding="utf-8")

text = text.replace(
    "result.reviewer_stats.total_rider_impact",
    "result.reviewer_stats.total_route_boardings_represented"
)

text = text.replace(
    "Your reviews have helped validate stops serving approximately",
    "Across the routes serving stops you reviewed, approximately"
)

text = text.replace(
    "weekday riders.",
    "weekday boardings are represented."
)

text = text.replace(
    "Your review helped validate a stop serving approximately",
    "Your review helped validate a stop served by routes representing approximately"
)

review.write_text(
    text,
    encoding="utf-8"
)


print("Updated route-level ridership language")