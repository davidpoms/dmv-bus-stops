from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

text = text.replace(
"""
        SELECT
            dc_anc,
            stop_count
        FROM dc_anc_summary
        ORDER BY dc_anc
""",
"""
        SELECT
            dc_anc,
            stop_count
        FROM dc_anc_summary
        WHERE dc_anc IS NOT NULL
        ORDER BY dc_anc
"""
)

p.write_text(text)

print("Filtered null ANC rows")
