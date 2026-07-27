from pathlib import Path


path = Path(
    "src/assessment/generate_impact_summary.py"
)

text = path.read_text()


old = """
        LEFT JOIN improvement_recommendations ir

            ON io.physical_stop_id = ir.physical_stop_id
"""


new = """
        LEFT JOIN improvement_recommendations ir

            ON io.physical_stop_id = ir.physical_stop_id
"""


# Keep join intact. We are changing generation logic instead.
if old not in text:
    raise SystemExit("Join block not found")


old_block = """
        recommendation_list = []

        if recommendations:

            recommendation_list = list(
                set(
                    recommendations.split(",")
                )
            )
"""


new_block = """
        recommendation_list = []

        if recommendations:

            recommendation_list = list(
                set(
                    recommendations.split(",")
                )
            )


        # Generate opportunity-based recommendations
        # when no volunteer recommendations exist yet.

        if not recommendation_list:

            assessment_score = (
                assessment
                .get("route_exposure", {})
                .get(
                    "combined_route_weekday_boardings",
                    0
                )
            )


            if opportunity_score >= 70:

                recommendation_list.append(
                    "priority_review"
                )


            if assessment_score > 0:

                recommendation_list.append(
                    "ridership_based_improvement_review"
                )
"""


if old_block not in text:
    raise SystemExit(
        "Recommendation block not found"
    )


text = text.replace(
    old_block,
    new_block
)


path.write_text(text)

print(
    "Updated impact summary recommendation generation"
)
