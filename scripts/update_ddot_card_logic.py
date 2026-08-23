from pathlib import Path

path = Path(
    "src/dashboard/static/stop_detail.js"
)

text = path.read_text(
    encoding="utf-8"
)


old = '''                item.finding &&
                    item.finding.includes(
                        "active shelter"
                    )
                )'''


new = '''                item.evidence_class ===
                    "current_asset"
                )'''


if old not in text:
    raise Exception(
        "Could not find DDOT shelter matcher block"
    )


text = text.replace(
    old,
    new,
    1
)


text = text.replace(
    '"✓ Confirmed present"',
    '"✓ DDOT shelter asset identified"',
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated DDOT shelter card logic"
)