from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_total,
"""


new = """    impact_summary = query_db(
        \"\"\"
        SELECT
            summary,
            impact_level,
            recommendations,
            opportunity_score,
            daily_route_exposure

        FROM stop_improvement_impact

        WHERE physical_stop_id = ?
        \"\"\",
        (stop_id,)
    )


    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_total,
"""


if old not in text:
    raise Exception("Could not find ridership query insertion point")


text = text.replace(old, new, 1)


old = """            "ridership_exposure":
                ridership_exposure
"""


new = """            "ridership_exposure":
                ridership_exposure,


            "impact_summary":
                {
                    "summary": impact_summary[0][0],
                    "impact_level": impact_summary[0][1],
                    "recommendations":
                        impact_summary[0][2].split(",")
                        if impact_summary[0][2]
                        else [],
                    "opportunity_score": impact_summary[0][3],
                    "daily_route_exposure": impact_summary[0][4]
                }
                if impact_summary
                else None
"""


if old not in text:
    raise Exception("Could not find return JSON block")


text = text.replace(old, new, 1)


path.write_text(text)

print("Added impact_summary to stop_detail")