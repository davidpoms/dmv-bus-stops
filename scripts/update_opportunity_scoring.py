from pathlib import Path

path = Path(
    "src/assessment/score_improvement_opportunities.py"
)

text = path.read_text()


old = """
        opportunity_score = (

            route_exposure_score * 0.45

            +

            connectivity_score * 0.20

            +

            amenity_gap_score * 0.35

        )
"""


new = """
        # Rider exposure is the primary driver.
        # Amenity gaps refine priorities but should not dominate
        # because missing OSM data is common.

        opportunity_score = (

            route_exposure_score * 0.70

            +

            connectivity_score * 0.15

            +

            amenity_gap_score * 0.15

        )
"""


if old not in text:
    print(
        "Could not find scoring block."
    )

    start = text.find(
        "opportunity_score ="
    )

    print(
        text[start:start+250]
    )

    raise SystemExit(1)


text = text.replace(
    old,
    new
)


path.write_text(
    text
)


print(
    "Updated opportunity scoring weights:"
)

print(
    "route=70%, network=15%, amenity_gap=15%"
)
