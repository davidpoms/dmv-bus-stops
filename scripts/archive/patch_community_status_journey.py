from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
    return jsonify(
        {
            "validation_status": validation_status,

            "validation": {
                "validator": validator,
                "validated_at": validated_at
            },

            "evidence": {
                "streetview_reviews": review_count,
                "field_observations": observation_count
            },

            "community_action": {
                "improvements": installed_projects
            }
        }
    )
"""


new = """
    required_reviews = 3


    streetview_status = (
        "consensus_reached"
        if review_count >= required_reviews
        else
        "awaiting_consensus"
    )


    field_review_status = (
        "completed"
        if validation_status == "validated"
        else
        "not_started"
    )


    return jsonify(
        {
            "journey": {

                "opportunity_identified": True,


                "streetview": {

                    "required_reviews":
                        required_reviews,

                    "completed_reviews":
                        review_count,

                    "status":
                        streetview_status
                },


                "field_review": {

                    "status":
                        field_review_status,

                    "validator":
                        validator,

                    "validated_at":
                        validated_at
                },


                "community_project": {

                    "status":
                        "active"
                        if installed_projects
                        else
                        "none",

                    "improvements":
                        installed_projects
                }

            }
        }
    )
"""


if old not in text:
    print("community status return block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


p.write_text(text)

print("community status journey patched")

