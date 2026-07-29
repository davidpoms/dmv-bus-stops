from pathlib import Path


path = Path(
    "src/review/create_review_queue.py"
)

text = path.read_text()


old_table = """
            review_status TEXT DEFAULT 'pending',

            review_questions JSON,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""


new_table = """
            review_status TEXT DEFAULT 'pending',

            review_questions JSON,

            consensus_status TEXT DEFAULT 'pending',

            resolution_reason TEXT,

            verification_needed INTEGER DEFAULT 1,

            community_review_available INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""


if old_table not in text:
    raise Exception(
        "Could not find table definition"
    )


text = text.replace(
    old_table,
    new_table
)


old_insert = """
                review_status,
                review_questions
            )

            VALUES (?, ?, ?, ?, ?, ?);
"""


new_insert = """
                review_status,
                review_questions,
                consensus_status,
                verification_needed,
                community_review_available
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


if old_insert not in text:
    raise Exception(
        "Could not find insert definition"
    )


text = text.replace(
    old_insert,
    new_insert
)


old_values = """
                location_name,
                "pending",
                json.dumps(questions)
            )
"""


new_values = """
                location_name,
                "pending",
                json.dumps(questions),
                "pending",
                1,
                1
            )
"""


if old_values not in text:
    raise Exception(
        "Could not find insert values"
    )


text = text.replace(
    old_values,
    new_values
)


path.write_text(text)


print(
    "✓ Updated review queue builder with consensus fields"
)
