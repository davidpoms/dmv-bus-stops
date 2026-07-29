from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def reviewer_progress_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM community_reviewers
            ) AS reviewers,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
            ) AS assignments,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='completed'
            ) AS completed_assignments,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='assigned'
            ) AS pending_assignments

        """
    )[0]

'''

if "def reviewer_progress_metrics" not in text:
    text += addition

p.write_text(text)

print("Added reviewer progress metrics")
