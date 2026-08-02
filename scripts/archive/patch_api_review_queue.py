from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """
        SELECT
            ir.physical_stop_id,
            ps.latitude AS lat,
            ps.longitude AS lon,
            ir.recommendation_type,
            ir.priority,
            ir.confidence,
            ir.reasons,
            ir.evidence

        FROM improvement_recommendations ir

        JOIN physical_stops ps
            ON ps.id = ir.physical_stop_id

        ORDER BY
            CASE ir.priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
            END,
            ir.physical_stop_id
"""

new = """
        SELECT
            rq.physical_stop_id,
            ps.latitude AS lat,
            ps.longitude AS lon,
            rq.priority_rank,
            rq.opportunity_score,
            rq.location_name,
            rq.review_status,
            rq.consensus_status

        FROM review_queue rq

        JOIN physical_stops ps
            ON ps.id = rq.physical_stop_id

        WHERE rq.review_status = 'pending'

        ORDER BY
            rq.priority_rank,
            rq.physical_stop_id
"""

if old not in text:
    raise Exception("Could not find old review queue query")

text = text.replace(old,new)

path.write_text(text)

print("Patched API review queue query")