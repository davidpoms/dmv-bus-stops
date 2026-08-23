from pathlib import Path

path = Path("src/review/create_review_queue.py")

text = path.read_text()

old = """
        WHERE w.wmata_status = 'PRS'

        ORDER BY io.priority_rank;
"""

new = """
        WHERE w.wmata_status = 'PRS'

        AND NOT EXISTS (

            SELECT 1

            FROM stop_wmata_evidence wx

            WHERE wx.physical_stop_id = ps.id

            AND wx.wmata_status = 'ABS'

        )

        ORDER BY io.priority_rank;
"""

if old not in text:
    raise Exception("Could not find current PRS filter block")

text = text.replace(old, new)

path.write_text(text)

print("Patched strict PRS filter")