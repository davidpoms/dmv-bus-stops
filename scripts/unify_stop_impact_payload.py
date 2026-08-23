from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(
    encoding="utf-8"
)


old_query = """
FROM physical_stops ps

JOIN improvement_opportunities io
    ON ps.id = io.physical_stop_id
"""


new_query = """
FROM physical_stops ps

LEFT JOIN stop_improvement_impact si
    ON ps.id = si.physical_stop_id
"""


if old_query not in text:
    raise Exception(
        "Old improvement_opportunities join not found"
    )


text = text.replace(
    old_query,
    new_query,
    1
)


text = text.replace(
    "io.opportunity_score",
    "si.opportunity_score",
    3
)


# Replace final score payload section
old_payload = """
"score":
    row[3],

"impact":
    row[4],
"""


new_payload = """
"score":
    row[3],

"impact":
    row[4],

"impact_summary":
    {
        "opportunity_score":
            row[3],

        "impact_level":
            row[4],

        "rider_exposure_percentile":
            rider_exposure_percentile,

        "daily_route_exposure":
            (
                impact_summary[0][4]
                if impact_summary
                else None
            ),

        "summary":
            (
                impact_summary[0][0]
                if impact_summary
                else None
            )
    },
"""


if old_payload not in text:
    raise Exception(
        "Score payload block not found"
    )


text = text.replace(
    old_payload,
    new_payload,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated stop impact payload"
)