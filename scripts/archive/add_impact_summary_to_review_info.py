from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


# Add impact query before streetview block
marker = """
    streetview = get_road_index().nearest_road(
        row[2],
        row[3]
    )
"""


insert = """
    impact_summary = query_db(
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


""" + marker


if marker not in text:
    raise Exception("Could not find streetview block")


text = text.replace(marker, insert, 1)


# Add JSON response field
old = """
            "ridership_exposure":
                ridership_exposure
"""

new = """
            "ridership_exposure":
                ridership_exposure,

            "impact_summary":
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


if old not in text:
    raise Exception("Could not find response insertion point")


text = text.replace(old, new, 1)


# Remove temporary debug prints
text = text.replace(
    '    print("RIDERSHIP QUERY RESULT:", ridership)\n',
    ''
)

text = text.replace(
    '    print("RIDERSHIP EXPOSURE:", ridership_exposure)\n',
    ''
)


path.write_text(text)

print("Added impact_summary to review_stop_info")