from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

if '"/api/stops/<int:stop_id>/review-summary"' in text:
    raise SystemExit("Endpoint already exists")

marker = '@app.route("/api/stops/<int:stop_id>/evidence")'

idx = text.find(marker)

if idx == -1:
    raise Exception("Evidence endpoint marker not found")


addition = r'''

@app.route("/api/stops/<int:stop_id>/review-summary")
def stop_review_summary(stop_id):

    evidence = get_stop_evidence_summary(stop_id)

    bench_status = interpret_bench_status(
        evidence
    )

    review_priority = interpret_review_priority(
        evidence,
        bench_status
    )

    review_actions = generate_review_action_summary(
        evidence,
        review_priority
    )


    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    stop = conn.execute(
        """
        SELECT
            id,
            primary_name,
            latitude,
            longitude
        FROM physical_stops
        WHERE id=?
        """,
        (stop_id,)
    ).fetchone()

    conn.close()


    return jsonify({

        "stop": dict(stop) if stop else None,

        "status": {
            "bench": bench_status,
            "priority": review_priority
        },

        "actions": review_actions,

        "evidence": evidence

    })



'''

text = text[:idx] + addition + text[idx:]

path.write_text(text)

print("Added review summary endpoint")
