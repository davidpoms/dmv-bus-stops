from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text()


old = """
    impact_summary =
"""


# Insert opportunity query after rider exposure block
marker = """
    streetview = get_road_index().nearest_road(
        row[2],
        row[3]
    )
"""


insert = """
    opportunity = query_db(
        '''
        SELECT
            opportunity_score,
            impact_level,
            daily_route_exposure,
            summary,
            recommendations
        FROM stop_improvement_impact
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    opportunity_summary = (
        {
            "score":
                opportunity[0][0],

            "level":
                opportunity[0][1],

            "daily_route_exposure":
                opportunity[0][2],

            "summary":
                opportunity[0][3],

            "recommendations":
                json.loads(opportunity[0][4])
                if opportunity[0][4]
                else []
        }
        if opportunity
        else None
    )


"""


if marker not in text:
    raise Exception("streetview insertion point not found")


text = text.replace(
    marker,
    insert + marker
)


old_response = """
            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile,

                    "estimated_weekday_boardings":
                        ridership_exposure["average_weekday_boardings"]
                        if ridership_exposure
                        else None,

                    "routes_served":
                        ridership_exposure["route_count"]
                        if ridership_exposure
                        else 0,

                    "routes":
                        ridership_exposure["routes"]
                        if ridership_exposure
                        else []
                }
"""


new_response = """
            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile,

                    "estimated_weekday_boardings":
                        ridership_exposure["average_weekday_boardings"]
                        if ridership_exposure
                        else None,

                    "routes_served":
                        ridership_exposure["route_count"]
                        if ridership_exposure
                        else 0,

                    "routes":
                        ridership_exposure["routes"]
                        if ridership_exposure
                        else [],

                    "opportunity_score":
                        opportunity_summary["score"]
                        if opportunity_summary
                        else None,

                    "impact_level":
                        opportunity_summary["level"]
                        if opportunity_summary
                        else None
                },


            "opportunity":
                opportunity_summary
"""


if old_response not in text:
    raise Exception("impact response block not found")


text = text.replace(
    old_response,
    new_response
)


path.write_text(text)

print("Updated review info impact payload")