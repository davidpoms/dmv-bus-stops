from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
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
"""


new = """
            AND (
                ? IS NULL

                OR (
                    ? = 'opportunity'
                    AND (
                        sv.status IS NULL
                        OR sv.status = 'needs_validation'
                    )
                )

                OR (
                    ? = 'candidate'
                    AND sv.status = 'validated'
                )
            )
"""


count = text.count(old)

if count == 0:
    print("review state block not found")
    raise SystemExit(1)


text = text.replace(old, new)

p.write_text(text)

print(
    f"patched {count} review state blocks"
)
