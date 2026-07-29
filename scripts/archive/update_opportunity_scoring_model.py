from pathlib import Path

path = Path(
    "src/assessment/score_improvement_opportunities.py"
)

text = path.read_text()


start = text.find(
    "        opportunity_score = ("
)

end = text.find(
    "        factors = {",
    start
)


if start == -1 or end == -1:
    print("Could not locate scoring section.")
    exit(1)


replacement = """        #
        # Opportunity score:
        # Measures where improvements matter most.
        #
        # Rider exposure dominates.
        # Amenity uncertainty is a smaller modifier.
        #

        opportunity_score = (

            route_exposure_score * 0.65

            +

            connectivity_score * 0.20

            +

            amenity_gap_score * 0.15

        )


        #
        # Verification priority:
        # Determines where volunteers should review stops.
        #
        # High ridership + incomplete amenity evidence
        # gets prioritized.
        #

        verification_priority_score = (

            route_exposure_score * 0.50

            +

            amenity_gap_score * 0.50

        )


"""


text = (
    text[:start]
    +
    replacement
    +
    text[end:]
)


# Insert verification score into factors JSON
marker = """            "amenity_gap": {
"""


if marker in text and "verification_priority" not in text:

    text = text.replace(
        marker,
        """            "verification_priority": {

                "score":
                    round(
                        verification_priority_score,
                        2
                    ),

                "reason":
                    "High rider exposure combined with incomplete amenity evidence"

            },


""" + marker
    )


path.write_text(text)

print(
    "Updated opportunity scoring model."
)
