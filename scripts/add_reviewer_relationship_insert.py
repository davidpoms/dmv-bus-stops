from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

# Add column after review_mode in INSERT column list
old_columns = """
            review_mode,
            rider_activity,
            usage_times,
"""

new_columns = """
            review_mode,
            reviewer_relationship,
            rider_activity,
            usage_times,
"""

if old_columns not in text:
    raise Exception("Could not find INSERT column block")

text = text.replace(
    old_columns,
    new_columns,
    1
)


# Add value after review_mode value
old_values = """
            # review_mode
            data.get("review_mode"),

            # activity
            data.get("rider_activity"),
"""

new_values = """
            # review_mode
            data.get("review_mode"),

            # reviewer relationship
            data.get("reviewer_relationship"),

            # activity
            data.get("rider_activity"),
"""

if old_values not in text:
    raise Exception("Could not find INSERT values block")

text = text.replace(
    old_values,
    new_values,
    1
)


p.write_text(text)

print("Added reviewer_relationship to INSERT mapping")
