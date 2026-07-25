from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def counties():
    return query(
        """
        SELECT
            state,
            county,
            stop_count
        FROM county_summary
        ORDER BY state, county
        """
    )


def municipalities():
    return query(
        """
        SELECT
            state,
            county,
            municipality,
            stop_count
        FROM municipality_summary
        ORDER BY state, county, municipality
        """
    )


def dc_ancs():
    return query(
        """
        SELECT
            dc_ward,
            dc_anc,
            stop_count
        FROM dc_anc_summary
        ORDER BY dc_ward, dc_anc
        """
    )

'''

if "def counties(" not in text:
    p.write_text(text + addition)

print("Added full geography metrics")
