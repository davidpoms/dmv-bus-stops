from pathlib import Path

path = Path("src/assessment/interpretation.py")

text = path.read_text()

if "def generate_review_action_summary" in text:
    raise SystemExit("Already exists")

addition = """

def generate_review_action_summary(evidence, review_priority):

    transit = evidence.get("transit") or {}
    osm = evidence.get("osm") or {}

    actions = []

    if transit.get("gtfs_bus_stop") == 1:
        actions.append(
            "Verify physical stop amenities"
        )

    if osm.get("osm_bench", 0) == 0:
        actions.append(
            "Confirm whether bench exists"
        )

    if osm.get("osm_shelter", 0) == 0:
        actions.append(
            "Confirm whether shelter exists"
        )

    if not evidence.get("reviews"):
        actions.append(
            "Collect first community observation"
        )

    return {
        "priority": review_priority["level"],
        "recommended_actions": actions
    }

"""

path.write_text(text + addition)

print("Added review action summary")
