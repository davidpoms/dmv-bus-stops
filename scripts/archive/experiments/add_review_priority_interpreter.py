from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = "\ndef interpret_bench_status(evidence):"

addition = """

def interpret_review_priority(evidence, bench_status):

    osm = evidence.get("osm")

    if bench_status["status"] == "confirmed_bench":
        return {
            "level": "low",
            "reasons": [
                "Bench already mapped"
            ]
        }

    if osm and osm.get("osm_shelter") == 1:
        return {
            "level": "medium",
            "reasons": [
                "Shelter mapped",
                "Bench status needs verification"
            ]
        }

    return {
        "level": "high",
        "reasons": [
            "No bench evidence",
            "Needs volunteer review"
        ]
    }

"""

if marker not in text:
    raise Exception("Marker not found")

text = text.replace(
    marker,
    addition + marker,
    1
)

p.write_text(text)

print("Added review priority interpreter")
