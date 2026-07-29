from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

if "/validation/update" not in text:

    marker = '@app.route("/validation/queue")'

    insert = r'''
@app.route("/validation/update", methods=["POST"])
def validation_update():

    data = request.json

    stop_id = data["stop_id"]
    status = data["status"]
    validator = data.get("validator", "")
    notes = data.get("notes", "")


    conn = sqlite3.connect(
        "src/database/dmv_bus_stops.db"
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        INSERT INTO stop_validation
        (
            physical_stop_id,
            status,
            validator,
            notes,
            validated_at
        )

        VALUES (?, ?, ?, ?, datetime('now'))

        ON CONFLICT(physical_stop_id)
        DO UPDATE SET

            status = excluded.status,
            validator = excluded.validator,
            notes = excluded.notes,
            validated_at = excluded.validated_at
        """,
        (
            stop_id,
            status,
            validator,
            notes
        )
    )


    conn.commit()
    conn.close()


    return jsonify(
        {
            "success": True,
            "stop_id": stop_id,
            "status": status
        }
    )


'''

    if marker in text:
        text = text.replace(
            marker,
            insert + marker,
            1
        )

        p.write_text(text)
        print("Validation update endpoint added")

    else:
        print("Validation queue route not found")

else:
    print("Validation update endpoint already exists")
