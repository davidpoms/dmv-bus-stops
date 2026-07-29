from pathlib import Path

path = Path("src/assessment/interpretation.py")

text = path.read_text()

old = '''def interpret_bench_status(evidence):

    osm = evidence.get("osm")

    if not osm:
'''

new = '''def interpret_bench_status(evidence):

    osm = evidence.get("osm")
    transit = evidence.get("transit")

    if not osm:
'''

if old not in text:
    raise Exception("bench function anchor not found")

text = text.replace(old, new)


old = '''    return {
        "status": "needs_review",
        "label": "Needs bench review",
        "confidence": "low",
        "observed": [
            "No bench mapped in OSM"
        ],
        "inferred": [
            "Physical verification recommended"
        ]
    }
'''

new = '''    observed = [
        "No bench mapped in OSM"
    ]

    if transit and transit.get("gtfs_bus_stop") == 1:
        observed.append(
            "Transit stop confirmed by GTFS"
        )

    return {
        "status": "needs_review",
        "label": "Needs bench review",
        "confidence": "medium",
        "observed": observed,
        "inferred": [
            "Physical verification recommended"
        ]
    }
'''

if old not in text:
    raise Exception("needs_review block not found")

text = text.replace(old, new)


old = '''def interpret_review_priority(evidence, bench_status, context=None):

    osm = evidence.get("osm")

    if bench_status["status"] == "confirmed_bench":
'''

new = '''def interpret_review_priority(evidence, bench_status, context=None):

    osm = evidence.get("osm")
    transit = evidence.get("transit")

    if bench_status["status"] == "confirmed_bench":
'''

if old not in text:
    raise Exception("priority function anchor not found")

text = text.replace(old, new)


old = '''    return {
        "level": "high",
        "reasons": [
            "No bench evidence",
            "Volunteer review needed"
        ]
    }
'''

new = '''    reasons = [
        "No bench evidence",
        "Volunteer review needed"
    ]

    if transit and transit.get("gtfs_bus_stop") == 1:
        reasons.insert(
            0,
            "Active transit stop confirmed"
        )

    return {
        "level": "high",
        "reasons": reasons
    }
'''

if old not in text:
    raise Exception("priority return block not found")

text = text.replace(old, new)


path.write_text(text)

print("Updated interpretation logic with transit evidence.")
