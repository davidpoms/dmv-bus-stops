from pathlib import Path

path = Path(
    "src/assessment/score_improvement_opportunities.py"
)

text = path.read_text()


marker = """        factors = {

"""


insert = """        factors = {

            "verification_priority": {

                "score":
                    round(
                        verification_priority_score,
                        2
                    ),

                "reason":
                    "High rider exposure combined with incomplete amenity evidence"

            },


"""


if '"verification_priority"' in text:
    print("verification_priority already exists")
    exit(0)


if marker not in text:
    print("Could not find factors block")
    exit(1)


text = text.replace(
    marker,
    insert,
    1
)


path.write_text(text)

print("Added verification_priority factor.")
