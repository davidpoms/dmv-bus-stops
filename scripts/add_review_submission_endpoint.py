from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

addition = r'''

@app.post("/api/reviews/submit")
def submit_review():

    data = request.json


    stop_id = data["stop_id"]
    reviewer_id = data["reviewer_id"]


    conn = sqlite3.connect(DB)
    cur = conn.cursor()


    assignment = cur.execute(
        """
        SELECT id
        FROM stop_review_assignments
        WHERE stop_id = ?
        AND reviewer_id = ?
        """,
        (
            stop_id,
            reviewer_id,
        )
    ).fetchone()


    if not assignment:

        conn.close()

        return {
            "error": "No assignment exists"
        }, 403



    cur.execute(
        """
        INSERT INTO stop_reviews
        (
            stop_id,

            reviewer_id,

            has_shelter,
            has_bench,
            bench_condition,

            waiting_area_type,
            likely_waiting_location,
            sun_exposure,

            concrete_pad_present,
            pad_width_feet,
            pad_depth_feet,

            bench_location_feasible,

            curb_access_clear,
            bus_ramp_access_clear,
            landing_zone_clear,
            rear_clear_zone_clear,

            reviewer_confidence,

            notes
        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (

            stop_id,
            reviewer_id,

            data.get("has_shelter"),
            data.get("has_bench"),
            data.get("bench_condition"),

            data.get("waiting_area_type"),
            data.get("likely_waiting_location"),
            data.get("sun_exposure"),

            data.get("concrete_pad_present"),
            data.get("pad_width_feet"),
            data.get("pad_depth_feet"),

            data.get("bench_location_feasible"),

            data.get("curb_access_clear"),
            data.get("bus_ramp_access_clear"),
            data.get("landing_zone_clear"),
            data.get("rear_clear_zone_clear"),

            data.get("reviewer_confidence"),

            data.get("notes"),

        )
    )


    cur.execute(
        """
        UPDATE stop_review_assignments

        SET
            status='completed',
            completed_at=CURRENT_TIMESTAMP

        WHERE id=?
        """,
        (
            assignment[0],
        )
    )


    conn.commit()
    conn.close()


    return {
        "success": True,
        "stop_id": stop_id
    }

'''

if "def submit_review" not in text:
    text += addition

p.write_text(text)

print("Added review submission endpoint")
