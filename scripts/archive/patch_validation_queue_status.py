from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
SELECT
    rq.physical_stop_id,
    rq.location_name,
    rq.priority_rank,
    rq.opportunity_score,
    rq.review_status

FROM review_queue rq
"""

new = """
SELECT
    rq.physical_stop_id,
    rq.location_name,
    rq.priority_rank,
    rq.opportunity_score,
    rq.review_status,

    COALESCE(
        COUNT(sr.id),
        0
    ) AS review_count,

    COALESCE(
        sv.status,
        'needs_validation'
    ) AS validation_status

FROM review_queue rq

LEFT JOIN stop_reviews sr
    ON rq.physical_stop_id = sr.stop_id

LEFT JOIN stop_validation sv
    ON rq.physical_stop_id = sv.physical_stop_id

GROUP BY
    rq.physical_stop_id
"""

if old in text:
    text = text.replace(old,new)
else:
    print("queue query block not found")

p.write_text(text)

print("validation queue status patched")
