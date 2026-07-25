from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

text = text.replace(
"""def top_counties(limit=10):
    return query(
        f"""
        SELECT
            state,
            county,
            stop_count
        FROM county_summary
        ORDER BY stop_count DESC
        LIMIT {limit}
        """
    )
""",
"""def counties():
    return query(
        """
        SELECT
            state,
            county,
            stop_count
        FROM county_summary
        ORDER BY state, stop_count DESC
        """
    )
"""
)

text = text.replace(
"""def top_municipalities(limit=10):
    return query(
        f"""
        SELECT
            state,
            county,
            municipality,
            stop_count
        FROM municipality_summary
        ORDER BY stop_count DESC
        LIMIT {limit}
        """
    )
""",
"""def municipalities():
    return query(
        """
        SELECT
            state,
            county,
            municipality,
            stop_count
        FROM municipality_summary
        ORDER BY state, county, stop_count DESC
        """
    )
"""
)

if "def dc_ancs" not in text:
    text += """

def dc_ancs():
    return query(
        '''
        SELECT
            anc,
            stop_count
        FROM dc_anc_summary
        ORDER BY anc
        '''
    )

"""

p.write_text(text)

print("Expanded geography metrics")
