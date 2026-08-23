from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


# 1. Add rider exposure query after impact_summary query
old_query = """    impact_summary = query_db(
        '''
        SELECT
            summary,
            impact_level,
            recommendations,
            opportunity_score,
            daily_route_exposure

        FROM stop_improvement_impact

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )
"""


new_query = old_query + """

    rider_exposure = query_db(
        '''
        SELECT
            assessment_json

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    rider_exposure_percentile = None


    if rider_exposure and rider_exposure[0][0]:

        try:

            assessment = json.loads(
                rider_exposure[0][0]
            )

            rider_exposure_percentile = (
                assessment.get(
                    "rider_exposure_percentile"
                )
            )

        except Exception:

            pass
"""


if old_query not in text:
    raise Exception(
        "Could not find impact_summary query block"
    )


text = text.replace(
    old_query,
    new_query,
    1
)


# 2. Replace API exposure block
old_block = """            "impact_summary":
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


new_block = """            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile
                }
"""


if old_block not in text:
    raise Exception(
        "Could not find impact_summary response block"
    )


text = text.replace(
    old_block,
    new_block,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated review_stop_info impact summary"
)