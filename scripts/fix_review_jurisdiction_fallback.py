from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''    if not stop:
        return "Stop not found", 404

    return render_template(
        "review.html",
        stop=stop[0],
        stop_id=stop_id,
        survey_html=render_survey()
    )
'''

new = '''    if not stop:
        return "Stop not found", 404

    stop_row = list(stop[0])

    # Fallback jurisdiction from coordinates
    if not stop_row[4]:
        lon = stop_row[3]

        if lon < -77.05:
            stop_row[4] = "Virginia"
        elif lon > -76.95:
            stop_row[4] = "Maryland"
        else:
            stop_row[4] = "District of Columbia"

    return render_template(
        "review.html",
        stop=stop_row,
        stop_id=stop_id,
        survey_html=render_survey()
    )
'''

if old not in text:
    raise Exception("review route block not found")

text = text.replace(old, new)

p.write_text(text)

print("Added jurisdiction fallback")
