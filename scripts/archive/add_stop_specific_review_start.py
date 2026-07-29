from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
    result = assign_stop(
        reviewer_id,
        scenario
    )
"""


new = """
    stop_id_requested = request.args.get(
        "stop_id"
    )


    if stop_id_requested:

        result = assign_stop(
            reviewer_id,
            scenario,
            stop_id=int(stop_id_requested)
        )

    else:

        result = assign_stop(
            reviewer_id,
            scenario
        )
"""


if old not in text:
    raise Exception("Could not find assign_stop call")


text=text.replace(
    old,
    new
)


p.write_text(text)

print("Added stop-specific review routing")
