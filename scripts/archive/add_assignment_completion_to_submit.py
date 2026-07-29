from pathlib import Path
import re


path = Path("src/review/submit_stop_review.py")

text = path.read_text()


old = """
    conn.commit()

    review_id = cursor.lastrowid

    conn.close()
"""


new = """
    review_id = cursor.lastrowid


    # Mark matching assignment completed
    cursor.execute(
        """
        UPDATE stop_review_assignments

        SET
            status='completed',
            completed_at=CURRENT_TIMESTAMP

        WHERE stop_id=?
        AND reviewer_id=?
        """,
        (
            data["stop_id"],
            data.get("reviewer_id")
        )
    )


    conn.commit()


    conn.close()
"""


if old not in text:
    raise Exception(
        "Target block not found"
    )


text = text.replace(
    old,
    new
)


path.write_text(text)

print(
    "Updated submit_stop_review.py"
)
