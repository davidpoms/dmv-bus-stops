from pathlib import Path

path = Path("src/review/create_review_queue.py")

text = path.read_text(encoding="utf-8")

marker = "\n    cursor.execute(\n        \"\"\"\n        WITH latest_wmata AS"

if marker not in text:
    raise Exception("Could not find latest_wmata query block")

create_block = """
    cursor.execute(
        \"\"\"
        CREATE TABLE IF NOT EXISTS review_queue (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            priority_rank INTEGER,

            opportunity_score REAL,

            location_name TEXT,

            review_status TEXT DEFAULT 'pending',

            review_questions JSON,

            consensus_status TEXT DEFAULT 'pending',

            resolution_reason TEXT,

            verification_needed INTEGER DEFAULT 1,

            community_review_available INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );
        \"\"\"
    )


    cursor.execute(
        \"\"\"
        DELETE FROM review_queue;
        \"\"\"
    )

"""

text = text.replace(marker, "\n" + create_block + marker, 1)

path.write_text(text, encoding="utf-8")

print("Restored review_queue CREATE TABLE block")