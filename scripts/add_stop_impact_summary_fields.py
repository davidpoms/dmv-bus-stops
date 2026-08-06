from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(
    encoding="utf-8"
)


old = """
"routes":
    ridership_exposure["routes"]
    if ridership_exposure
    else []
"""


new = """
"routes":
    ridership_exposure["routes"]
    if ridership_exposure
    else [],


"opportunity_score":
    (
        impact_summary[0][3]
        if impact_summary
        else None
    ),


"impact_level":
    (
        impact_summary[0][1]
        if impact_summary
        else None
    ),


"daily_route_exposure":
    (
        impact_summary[0][4]
        if impact_summary
        else None
    ),


"recommendations":
    (
        json.loads(impact_summary[0][2])
        if impact_summary and impact_summary[0][2]
        else []
    ),


"summary":
    (
        impact_summary[0][0]
        if impact_summary
        else None
    )
"""


if old not in text:
    raise Exception(
        "Impact summary routes block not found"
    )


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
    "Added unified impact fields"
)