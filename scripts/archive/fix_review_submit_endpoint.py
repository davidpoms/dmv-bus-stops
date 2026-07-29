from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

start = text.index('@app.route("/review/submit"')
end = text.index('@app.route("/priorities/top")')

replacement = r'''
@app.route("/review/submit", methods=["POST"])
def submit_review():

    data = request.json


    query_db(
        """
        INSERT INTO stop_reviews
        (
            stop_id,
            user_id,
            anonymous_email,
            waiting_area_type,
            concrete_pad_present,
            bench_location_feasible,
            sun_exposure,
            reviewer_confidence,
            notes
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("stop_id"),
            data.get("user_id"),
            data.get("anonymous_email"),
            data.get("waiting_area_type"),
            data.get("concrete_pad_present"),
            data.get("bench_location_feasible"),
            data.get("sun_exposure"),
            data.get("reviewer_confidence"),
            data.get("notes")
        )
    )


    return jsonify(
        {
            "status":"saved"
        }
    )


'''

text = text[:start] + replacement + text[end:]

p.write_text(text)

print("Fixed review endpoint")
