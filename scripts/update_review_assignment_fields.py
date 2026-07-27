from pathlib import Path

p = Path("src/dashboard/templates/review.html")

text = p.read_text()

marker = '<form id="reviewForm">'

insert = '''
<form id="reviewForm">

<input type="hidden" name="reviewer_id" id="reviewer_id">

<input type="hidden" name="assignment_id" id="assignment_id">

'''

if marker in text and 'name="assignment_id"' not in text:

    text = text.replace(
        marker,
        insert
    )

    p.write_text(text)

    print("Added assignment fields")

else:
    print("Fields already exist or marker missing")

