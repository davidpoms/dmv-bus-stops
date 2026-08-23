from pathlib import Path


FILE = Path("src/api/app.py")


text = FILE.read_text()


marker = """
    return jsonify(
"""


insert = """
    opportunity_row = query_db(
        '''
        SELECT
            opportunity_score,
            impact_level
        FROM stop_improvement_impact
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    opportunity_summary = {

        "score":
            opportunity_row[0][0]
            if opportunity_row
            else None,

        "impact_level":
            opportunity_row[0][1]
            if opportunity_row
            else None

    }


"""


if marker not in text:
    raise Exception(
        "Return marker not found"
    )


if "opportunity_summary =" in text:
    raise Exception(
        "opportunity_summary already exists"
    )


text = text.replace(
    marker,
    insert + marker,
    1
)


FILE.write_text(text)


print(
    "Added opportunity_summary payload"
)