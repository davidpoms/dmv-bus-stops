from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def consensus_progress_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM physical_stops
            ) AS total_stops,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
            ) AS total_assignments,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='completed'
            ) AS completed_reviews,

            (
                SELECT COUNT(*)
                FROM stop_consensus
                WHERE consensus_status='verified'
            ) AS verified_stops,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='assigned'
            ) AS pending_reviews

        """
    )[0]

'''

if "def consensus_progress_metrics" not in text:
    p.write_text(text + addition)

print("Added consensus progress metrics")
