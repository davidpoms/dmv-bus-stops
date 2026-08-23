from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

route_marker = '@app.route("/api/stops/<int:stop_id>/evidence")'
main_marker = 'if __name__ == "__main__":'

route_pos = text.find(route_marker)
main_pos = text.find(main_marker)

if route_pos == -1:
    raise Exception("Evidence route not found")

if main_pos == -1:
    raise Exception("__main__ block not found")

if route_pos < main_pos:
    print("Route already before app.run")
    raise SystemExit

route_block = text[route_pos:main_pos]

text = (
    text[:route_pos]
    +
    text[main_pos:route_pos]
)

main_pos = text.find(main_marker)

text = (
    text[:main_pos]
    +
    route_block
    +
    "\n\n"
    +
    text[main_pos:]
)

p.write_text(text)

print("Moved evidence route before app.run")
