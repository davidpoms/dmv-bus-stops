from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
            p.state,
            p.dc_ward,
            p.dc_anc,
            p.county,
            p.municipality,
"""

new = """
            p.state,
            p.dc_ward,
            p.dc_anc,
            p.county,
            p.municipality,
"""

# no SQL change needed, state already exists
# replace jurisdiction fallback logic instead

old2 = """
    # Fallback jurisdiction from coordinates
    if not stop_row[4]:
        lon = stop_row[3]

        if lon < -77.05:
            stop_row[4] = "Virginia"
        elif lon > -76.95:
            stop_row[4] = "Maryland"
        else:
            stop_row[4] = "District of Columbia"
"""

new2 = """
    # Normalize displayed jurisdiction from state field
    if stop_row[4] == "MD/VA":
        stop_row[4] = "Maryland / Virginia"
"""

if old2 not in text:
    raise Exception("Could not find jurisdiction fallback block")

text = text.replace(old2, new2)

p.write_text(text)

print("Fixed review jurisdiction display")
