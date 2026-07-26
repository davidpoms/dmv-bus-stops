from pathlib import Path


p = Path("src/dashboard/data.py")

text = p.read_text()


# Replace community verification metrics
old_start = text.index(
    "def community_verification_metrics():"
)

old_end = text.index(
    "\n\ndef bench_metrics():",
    old_start
)

new_block = r'''def community_verification_metrics():

    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM physical_stops
            ) AS total_stops,


            (
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
            ) AS reviewed_stops,


            (
                SELECT COUNT(*)
                FROM stop_observations
            ) AS total_reviews,


            (
                SELECT COUNT(*)
                FROM physical_stops
                WHERE id NOT IN (
                    SELECT DISTINCT physical_stop_id
                    FROM stop_observations
                )
            ) AS awaiting_review,


            (
                SELECT COUNT(*)
                FROM stop_consensus
                WHERE consensus_status='verified'
            ) AS consensus_stops

        """
    )[0]
'''


text = (
    text[:old_start]
    + new_block
    + text[old_end:]
)


# Replace bench metrics
old_start = text.index(
    "def stop_level_bench_metrics():"
)

old_end = text.index(
    "\n\ndef counties():",
    old_start
)


new_block = r'''def stop_level_bench_metrics():

    return query(
        """
        SELECT


            (
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
                WHERE bench_present='yes'
            ) AS community_confirmed_benches,


            (
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
                WHERE bench_present='no'
                AND bench_feasible='yes'
            ) AS community_bench_opportunities,


            (
                SELECT COUNT(*)
                FROM physical_stops ps
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM stop_observations so
                    WHERE so.physical_stop_id = ps.id
                )
            ) AS stops_needing_review

        """
    )[0]
'''


text = (
    text[:old_start]
    + new_block
    + text[old_end:]
)


p.write_text(text)

print("Dashboard metrics updated:")
print("- community_verification_metrics now uses stop_observations + stop_consensus")
print("- stop_level_bench_metrics now uses stop_observations")
