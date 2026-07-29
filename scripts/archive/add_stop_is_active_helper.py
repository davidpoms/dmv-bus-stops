from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()

needle = """
def assign_stop(
"""

insert = """
def stop_is_active(stop_id):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    row = cur.execute(
        \"\"\"
        SELECT
            wmata_status
        FROM stop_wmata_evidence
        WHERE physical_stop_id=?
        \"\"\",
        (stop_id,)
    ).fetchone()

    conn.close()

    if not row:
        return True

    status = row[0]

    # WMATA statuses:
    # PRS = published/active stop
    # ABS = abandoned/inactive stop
    # Other unknown values are allowed for now

    if status == "ABS":
        return False

    return True



def assign_stop(
"""

if needle not in text:
    raise Exception("Could not find assign_stop insertion point")

text = text.replace(
    needle,
    insert,
    1
)

p.write_text(text)

print("Added stop_is_active helper")
