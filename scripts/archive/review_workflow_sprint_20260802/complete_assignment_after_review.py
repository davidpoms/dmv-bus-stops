from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

needle = """
    query_db(
        '''
        INSERT INTO stop_reviews
"""

insert = """
    query_db(
        '''
        UPDATE stop_review_assignments
        SET
            status='completed',
            completed_at=CURRENT_TIMESTAMP
        WHERE id=?
        ''',
        (
            assignment_id,
        )
    )


"""

if needle in text:
    text=text.replace(
        needle,
        insert + needle,
        1
    )
    print("Added assignment completion")

else:
    print("Insert point not found")

p.write_text(text)
