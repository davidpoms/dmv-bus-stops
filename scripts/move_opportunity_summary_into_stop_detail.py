from pathlib import Path


FILE = Path("src/api/app.py")


text = FILE.read_text()


# Existing block from the later endpoint
old = """
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


# The stop_detail return block
marker = """
    return jsonify(
        {
            "stop_id": stop_id,
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
    raise Exception(
        "stop_detail return marker not found"
    )


# Insert only if not already before stop_detail return
before_return = text.split(marker)[0]

if "opportunity_summary =" in before_return:
    raise Exception(
        "stop_detail already has opportunity_summary"
    )


text = text.replace(
    marker,
    insert + marker,
    1
)


FILE.write_text(text)


print(
    "Inserted opportunity_summary into stop_detail"
)