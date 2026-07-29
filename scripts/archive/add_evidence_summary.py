from pathlib import Path

path = Path("src/assessment/interpretation.py")

text = path.read_text()

if "def summarize_stop_evidence" in text:
    raise SystemExit("Already added")

addition = """

def summarize_stop_evidence(evidence):

    osm = evidence.get("osm") or {}
    transit = evidence.get("transit") or {}
    reviews = evidence.get("reviews") or []

    return {
        "transit_confirmed":
            transit.get("gtfs_bus_stop", 0) == 1,

        "osm_features": {
            "bench":
                osm.get("osm_bench", 0) == 1,

            "shelter":
                osm.get("osm_shelter", 0) == 1
        },

        "community_reviews":
            len(reviews),

        "data_sources": [
            source
            for source, present in [
                ("GTFS", transit.get("gtfs_bus_stop", 0)),
                ("OSM", osm.get("osm_feature_id")),
                ("Community Review", len(reviews))
            ]
            if present
        ]
    }

"""

path.write_text(text + addition)

print("Added evidence summary helper")
