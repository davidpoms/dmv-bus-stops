from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = '@app.route("/pipeline/geography")'

if marker not in text:
    raise Exception("pipeline route not found")

route_start = text.index(marker)
main_start = text.index('if __name__ == "__main__":')

route_block = text[route_start:]

# remove route block from bottom
text = text[:route_start]

# remove trailing whitespace
text = text.rstrip() + "\n\n"

# insert before main
text = text[:main_start] + route_block + "\n\n" + text[main_start:]

p.write_text(text)

print("Moved pipeline geography route above Flask startup")
