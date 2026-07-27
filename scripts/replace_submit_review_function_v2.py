from pathlib import Path

p = Path("src/api/app.py")
text = p.read_text()

start = text.find('@app.route("/review/submit"')

if start == -1:
    raise Exception("Could not find /review/submit route")


# Find the next Flask route after submit_review
end = text.find('@app.route(', start + 10)

if end == -1:
    raise Exception("Could not find next Flask route after submit_review")


new_function = r'''
@app.route("/review/submit", methods=["POST"])
def submit_review():

    data = request.json

    print("DEBUG REVIEW PAYLOAD:")
    print(data)


    data["shelter_type"] = data.get(
        "shelter_protection",
        data.get("shelter_type", "")
    )

    data["bench_type"] = data.get(
        "seating_type",
        data.get("bench_type", "")
    )

    data["bench_condition"] = data.get(
        "seating_limitations",
        data.get("bench_condition", "")
    )

    data["rider_comfort_category"] = data.get(
        "waiting_environment_rating",
        data.get("rider_comfort_category", "")
    )

    data["property_owner_outreach"] = data.get(
        "steward_interest",
        ""
    )

    data["steward_candidate"] = (
        1
        if data.get("steward_interest") in ("yes", "maybe")
        else 0
    )


    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")
    assignment_id = data.get("assignment_id")


    if not assignment_id or not reviewer_id:
        return {
            "error": "assignment_id and reviewer_id required"
        }, 400


    query_db(
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
            bench_type,
            bench_condition,
            shelter_type,
            rider_comfort_category,
            accessibility_status,
            notes,
            reviewer_id,
            confidence,
            source,
            review_mode,
            reviewer_relationship,
            rider_activity,
            usage_times,
            property_owner_outreach,
            steward_email,
            steward_candidate,
            concrete_pad_needed
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stop_id,
            data.get("observer", ""),
            data.get("shelter_present"),
            "yes" if data.get("bench_type") else data.get("bench_present"),
            data.get("trash_present"),
            data.get("bench_feasible"),
            data.get("accessibility_status"),
            data.get("bench_type", ""),
            data.get("bench_condition", ""),
            data.get("shelter_type", ""),
            data.get("rider_comfort_category", ""),
            data.get("accessibility_status"),
            data.get("notes"),
            reviewer_id,
            data.get("reviewer_confidence", "unknown"),
            "community_review",
            data.get("review_mode"),
            data.get("reviewer_relationship"),
            data.get("rider_activity"),
            data.get("usage_times"),
            data.get("property_owner_outreach", ""),
            data.get("steward_email"),
            data.get("steward_candidate", 0),
            data.get("concrete_pad_needed")
        )
    )


    query_db(
        """
        UPDATE stop_review_assignments
        SET status='completed',
            completed_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (assignment_id,)
    )


    return {
        "success": True,
        "stop_id": stop_id
    }


'''

text = text[:start] + new_function + text[end:]

p.write_text(text)

print("Replaced submit_review function")
