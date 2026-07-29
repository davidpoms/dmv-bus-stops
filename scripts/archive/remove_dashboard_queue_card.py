from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = "Community Review Queue"

pos = text.find(marker)

if pos == -1:
    raise SystemExit("Queue text not found")

start = text.rfind('<div class="card">', 0, pos)

if start == -1:
    raise SystemExit("Card start not found")


# find next card after this one
end = text.find('<div class="card">', pos)

if end == -1:
    # if last card, remove to end
    end = len(text)


text = text[:start] + text[end:]

p.write_text(text)

print("Removed dashboard queue card")
