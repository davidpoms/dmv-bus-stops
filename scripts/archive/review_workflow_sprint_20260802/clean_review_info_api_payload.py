from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
            "impact_summary":
                {
                    "summary": impact_summary[0][0],
                    "impact_level": impact_summary[0][1],
                    "recommendations":
                        json.loads(impact_summary[0][2])
                        if impact_summary[0][2]
                        else [],
                    "opportunity_score": impact_summary[0][3],
                    "daily_route_exposure": impact_summary[0][4]
                }
                if impact_summary
                else None
"""


new = """
            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile
                }
                if impact_summary
                else None
"""


count = text.count(old)

print("Matching blocks:", count)


if count == 0:
    raise Exception(
        "Could not find review impact_summary payload"
    )


# Replace only the review endpoint block
text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Cleaned review info API payload"
)