from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

if "action_filter = request.args.get(\"action\")" not in text:
    text = text.replace(
        'review_mode = request.args.get("review")',
        'review_mode = request.args.get("review")\n    action_filter = request.args.get("action")'
    )


old = """
            ORDER BY sii.opportunity_score DESC;
"""

new = """
            AND (
                ? IS NULL
                OR ca.status = ?
            )

            ORDER BY sii.opportunity_score DESC;
"""


count = text.count(old)

if count == 0:
    print("ORDER BY blocks not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)

p.write_text(text)

print(f"patched {count} map action filters")
