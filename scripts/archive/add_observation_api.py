from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = '@app.route("/validation/update", methods=["POST"])'

insert = '''

@app.route("/observations/create", methods=["POST"])
def create_observation():

    data = request.json

    conn = sqlite3.connect(DATABASE_PATH)

    conn.execute(
        """
        INSERT INTO stop_observations
        (
            physical_stop_id,
            observer,
            shelter_present,
            bench_present,
            trash_present,
            bench_feasible,
            ada_clearance_possible,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["stop_id"],
            data.get("observer", ""),
            data.get("shelter_present"),
            data.get("bench_present"),
            data.get("trash_present"),
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("notes", "")
        )
    )

    conn.commit()
    conn.close()

    return jsonify(
        {
            "success": True,
            "stop_id": data["stop_id"]
        }
    )


'''

if "/observations/create" not in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)
    print("Added observation API")
else:
    print("Observation API already exists")
