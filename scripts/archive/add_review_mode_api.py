from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
    dc_ward = request.args.get("dc_ward")
"""


new = """
    dc_ward = request.args.get("dc_ward")

    review_mode = request.args.get("review")
"""


if old not in text:
    print("request args block not found")
    raise SystemExit(1)


text = text.replace(old,new)


old2 = """
            AND (
                ? IS NULL
                OR sj.dc_ward = ?
            )

            ORDER BY sii.opportunity_score DESC;
"""


new2 = """
            AND (
                ? IS NULL
                OR sj.dc_ward = ?
            )

            AND (
                ? IS NULL
                OR (
                    ? = 'needed'
                    AND (
                        sv.status IS NULL
                        OR sv.status = 'needs_validation'
                    )
                )
                OR (
                    ? = 'validated'
                    AND sv.status = 'validated'
                )
            )

            ORDER BY sii.opportunity_score DESC;
"""


if old2 not in text:
    print("query block not found")
    raise SystemExit(1)


text = text.replace(old2,new2)


# add params twice in both query parameter tuples
text = text.replace(
"""
                dc_ward,
                dc_ward
            )
""",
"""
                dc_ward,
                dc_ward,
                review_mode,
                review_mode,
                review_mode
            )
"""
)


p.write_text(text)

print("review mode API added")
