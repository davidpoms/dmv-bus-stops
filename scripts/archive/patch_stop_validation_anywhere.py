from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


# Replace the old join regardless of spacing
text = text.replace(
    "LEFT JOIN stop_validation sv",
    """LEFT JOIN (
                SELECT
                    physical_stop_id,
                    'validated' AS status
                FROM stop_observations
                GROUP BY physical_stop_id
            ) sv"""
)


path.write_text(text)

print("Patched stop_validation references.")
print("Remaining stop_validation count:", text.count("stop_validation"))