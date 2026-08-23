from pathlib import Path

path = Path("src/scoring/calculate_stop_priority.py")

text = path.read_text()

old = """max_score_base = max(

        math.log(
            1 + (row[2] or 0)
        )

        for row in rows

    )
"""

new = """max_score_base = max(

        math.log(
            1 + (row[2] or 0)
        )

        for row in rows

    )


    if max_score_base == 0:
        max_score_base = 1
"""

if old not in text:
    raise Exception("Could not find max_score_base block")

text = text.replace(old, new)


old2 = """route_score = (

            routes_served
            /
            max_routes
            *
            100

        )
"""

new2 = """route_score = (

            routes_served
            /
            max_routes
            *
            100

        ) if max_routes else 0
"""

if old2 not in text:
    raise Exception("Could not find route_score block")

text = text.replace(old2, new2)


path.write_text(text)

print("Patched calculate_stop_priority.py")