from pathlib import Path

path = Path("scripts/rebuild_stop_consensus.py")
text = path.read_text()

# ------------------------------------------------------------------
# Replace observation query
# ------------------------------------------------------------------

old = '''
    rows = cur.execute(
        """
        SELECT

            bench_present,
            bench_feasible,
            ada_clearance_possible,
            confidence

        FROM stop_observations

        WHERE physical_stop_id=?

        AND reviewer_id IS NOT NULL

        """,
        (stop_id,)
    ).fetchall()
'''

new = '''
    rows = cur.execute(
        """
        SELECT
            bench_present,
            bench_feasible,
            ada_clearance_possible,
            confidence

        FROM stop_observations

        WHERE id IN
        (
            SELECT MAX(id)

            FROM stop_observations

            WHERE physical_stop_id=?

            AND reviewer_id IS NOT NULL

            GROUP BY reviewer_id
        )

        """,
        (stop_id,)
    ).fetchall()
'''

if old in text:
    text = text.replace(old, new)
    print("✓ Updated observation query")
else:
    print("⚠ Observation query not found")

# ------------------------------------------------------------------
# Replace reviewer_count calculation
# ------------------------------------------------------------------

start = text.find("reviewer_count = len(")

if start != -1:

    end = text.find("bench_yes =", start)

    replacement = '''
    reviewer_count = len(rows)

    print(f"DEBUG stop {stop_id}")
    print(rows)

'''

    text = text[:start] + replacement + text[end:]

    print("✓ Simplified reviewer_count")
else:
    print("⚠ reviewer_count block not found")

path.write_text(text)

print("Done.")
