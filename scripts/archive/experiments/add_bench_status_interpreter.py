from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = "\ndef get_stop_evidence_summary(stop_id):"

addition = """

def interpret_bench_status(evidence):

    osm = evidence.get("osm")

    if not osm:
        return {
            "status": "unknown",
            "label": "No evidence yet"
        }

    if osm["osm_bench"] == 1:
        return {
            "status": "confirmed_bench",
            "label": "Confirmed bench"
        }

    if osm["osm_shelter"] == 1:
        return {
            "status": "likely_bench_candidate",
            "label": "Shelter present, bench needs verification"
        }

    return {
        "status": "needs_review",
        "label": "Needs bench review"
    }

"""

if marker not in text:
    raise Exception("Function marker not found")

text = text.replace(
    marker,
    addition + marker,
    1
)

p.write_text(text)

print("Added bench status interpreter")
