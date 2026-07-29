from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = '@app.route("/priorities/top")'

endpoint = r'''

@app.route("/review/submit", methods=["POST"])
def submit_review():

    data = request.json


    stop_id = data.get("stop_id")

    user_id = data.get("user_id")

    anonymous_email = data.get(
        "anonymous_email"
    )


    has_bench = data.get(
        "has_bench"
    )

    has_space = data.get(
        "has_space_for_bench"
    )

    notes = data.get(
        "notes"
    )


    query_db(
        """
        INSERT INTO stop_reviews
        (
            stop_id,
            user_id,
            anonymous_email,
            has_bench,
            has_space_for_bench,
            notes
        )

        VALUES
        (?, ?, ?, ?, ?, ?)
        """,
        (
            stop_id,
            user_id,
            anonymous_email,
            has_bench,
            has_space,
            notes
        )
    )


    return jsonify(
        {
            "status": "saved"
        }
    )

'''

if 'def submit_review()' not in text:
    text = text.replace(
        marker,
        endpoint + "\n" + marker
    )

    p.write_text(text)

    print("Added review submission endpoint")
else:
    print("Endpoint already exists")
