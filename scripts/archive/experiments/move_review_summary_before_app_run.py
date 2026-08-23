from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

route = '@app.route("/api/stops/<int:stop_id>/review-summary")'

route_start = text.find(route)

main_start = text.find('if __name__ == "__main__":')

if route_start == -1:
    raise Exception("review-summary route not found")

if main_start == -1:
    raise Exception("__main__ block not found")

if route_start < main_start:
    print("Route already before app.run")
    raise SystemExit

route_block = text[route_start:main_start]

text = (
    text[:route_start]
    +
    text[main_start:]
)

main_start = text.find('if __name__ == "__main__":')

text = (
    text[:main_start]
    +
    route_block
    +
    "\n\n"
    +
    text[main_start:]
)

path.write_text(text)

print("Moved review-summary endpoint before app.run")
