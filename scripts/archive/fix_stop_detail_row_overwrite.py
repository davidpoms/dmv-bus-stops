from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """    for row in recommendations:

        recommendation_payload.append(
            {
                "type": row[0],
                "priority": row[1],
                "confidence": row[2],
                "evidence": json.loads(row[3]) if row[3] else {},
                "reasons": json.loads(row[4]) if row[4] else []
            }
        )
"""


new = """    for rec_row in recommendations:

        recommendation_payload.append(
            {
                "type": rec_row[0],
                "priority": rec_row[1],
                "confidence": rec_row[2],
                "evidence": json.loads(rec_row[3]) if rec_row[3] else {},
                "reasons": json.loads(rec_row[4]) if rec_row[4] else []
            }
        )
"""


if old not in text:
    raise Exception("Could not find recommendation loop")


text = text.replace(old, new, 1)


path.write_text(text)

print("Fixed stop_detail row overwrite")