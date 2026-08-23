from pathlib import Path

path = Path(
    "src/dashboard/static/stop_detail.js"
)

text = path.read_text(
    encoding="utf-8"
)


text = text.replace(
    '"âœ“ DDOT shelter asset identified"',
    '"&#10003; DDOT shelter asset identified"'
)


text = text.replace(
    '${item.source}',
    '${item.public_status || item.source}'
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated DDOT evidence card labels"
)