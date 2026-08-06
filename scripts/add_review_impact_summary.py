from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """
    rider_exposure = query_db(
        '''
        SELECT
            assessment_json

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )
"""


new = """
    rider_exposure = query_db(
        '''
        SELECT
            assessment_json

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    impact_row = query_db(
        '''
        SELECT
            opportunity_score,
            impact_level,
            daily_route_exposure

        FROM stop_improvement_impact

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    impact_summary = None


    if impact_row:

        impact_summary = {
            "opportunity_score":
                impact_row[0][0],

            "impact_level":
                impact_row[0][1],

            "estimated_weekday_boardings":
                round(impact_row[0][2])
                if impact_row[0][2]
                else 0,

            "rider_exposure_percentile":
                None
        }


    if rider_exposure:

        try:

            assessment = json.loads(
                rider_exposure[0][0]
            )

            impact_summary["rider_exposure_percentile"] = (
                assessment.get(
                    "rider_exposure_percentile"
                )
            )

        except Exception:
            pass
"""


if old not in text:
    raise Exception(
        "Could not find rider exposure query block"
    )


text = text.replace(old,new)


# add response field
old2 = """
        "ridership_exposure":
            ridership_exposure,
"""

new2 = """
        "ridership_exposure":
            ridership_exposure,

        "impact_summary":
            impact_summary,
"""


if old2 not in text:
    raise Exception(
        "Could not find response block"
    )


text=text.replace(old2,new2)


path.write_text(text)

print(
    "Updated review info impact summary"
)