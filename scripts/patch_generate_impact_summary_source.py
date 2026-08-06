from pathlib import Path


FILE = Path("src/assessment/generate_impact_summary.py")


text = FILE.read_text()


# Replace the old SQL query source
old_query = """
        SELECT

            io.physical_stop_id,

            oa.combined_route_weekday_boardings,

            io.opportunity_score,

            oa.assessment_json,

            GROUP_CONCAT(
                ir.recommendation_type
            )

        FROM improvement_opportunities io

        JOIN opportunity_assessments oa

            ON io.physical_stop_id = oa.physical_stop_id

        LEFT JOIN improvement_recommendations ir

            ON io.physical_stop_id = ir.physical_stop_id

        GROUP BY

            io.physical_stop_id,

            oa.combined_route_weekday_boardings,

            io.opportunity_score,

            oa.assessment_json

        ORDER BY

            io.opportunity_score DESC;
"""


new_query = """
        SELECT

            io.physical_stop_id,

            io.factors,

            io.opportunity_score,

            GROUP_CONCAT(
                ir.recommendation_type
            )

        FROM improvement_opportunities io

        LEFT JOIN improvement_recommendations ir

            ON io.physical_stop_id = ir.physical_stop_id

        GROUP BY

            io.physical_stop_id,

            io.factors,

            io.opportunity_score

        ORDER BY

            io.opportunity_score DESC;
"""


if old_query not in text:
    raise Exception(
        "Old impact summary SQL block not found"
    )


text = text.replace(
    old_query,
    new_query
)


# Replace unpacking
old_unpack = """
        (
            stop_id,
            daily_route_exposure,
            opportunity_score,
            assessment_json,
            recommendations
        ) = row


        assessment = json.loads(
            assessment_json
        )
"""


new_unpack = """
        (
            stop_id,
            factors_json,
            opportunity_score,
            recommendations
        ) = row


        factors = json.loads(
            factors_json
        )


        daily_route_exposure = (
            factors
            .get("route_exposure", {})
            .get(
                "combined_route_weekday_boardings",
                0
            )
        )
"""


if old_unpack not in text:
    raise Exception(
        "Old unpack block not found"
    )


text = text.replace(
    old_unpack,
    new_unpack
)


# Replace remaining assessment references
text = text.replace(
    "assessment\n                .get(\"route_exposure\", {})",
    "factors\n                .get(\"route_exposure\", {})"
)


FILE.write_text(text)


print(
    "Patched generate_impact_summary.py"
)