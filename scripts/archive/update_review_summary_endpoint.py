from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find('@app.route("/stops/<int:stop_id>/review-summary")')

if start == -1:
    raise Exception("review-summary endpoint not found")

end = text.find('\n@app.route', start + 10)

if end == -1:
    end = len(text)

new_endpoint = r'''
@app.route("/stops/<int:stop_id>/review-summary")
def stop_review_summary(stop_id):

    evidence = get_stop_evidence_summary(stop_id)

    transit = evidence.get("transit") or {}
    osm = evidence.get("osm") or {}
    reviews = evidence.get("reviews") or []

    reasons = []

    if transit.get("gtfs_bus_stop"):
        reasons.append(
            "Active transit stop confirmed"
        )

    if not osm.get("osm_bench"):
        reasons.append(
            "No OSM bench evidence"
        )

    if not osm.get("osm_shelter"):
        reasons.append(
            "No OSM shelter evidence"
        )

    if len(reviews) == 0:
        reasons.append(
            "No community observations"
        )


    return jsonify(
        {
            "stop_id": stop_id,

            "review_status": {
                "needs_field_review": len(reasons) > 0,
                "reasons": reasons
            },

            "evidence": {
                "gtfs_confirmed":
                    bool(transit.get("gtfs_bus_stop")),

                "osm_bench":
                    bool(osm.get("osm_bench")),

                "osm_shelter":
                    bool(osm.get("osm_shelter")),

                "community_reviews":
                    len(reviews)
            },

            "recommended_actions": [
                "Verify bench presence",
                "Verify shelter presence",
                "Collect first community observation"
            ]
        }
    )
'''

text = text[:start] + new_endpoint + text[end:]

path.write_text(text)

print("Updated review summary endpoint")
