from pathlib import Path

path = Path("dmv_bus_stops_dashboard.html")

text = path.read_text()


start_terms = [
    "Consensus Verification Pipeline",
    "Community Verification Progress"
]


start = -1

for term in start_terms:
    idx = text.find(term)
    if idx != -1:
        start = idx
        break


if start == -1:
    raise SystemExit("Could not find old metrics section")


# walk backward to nearest h2
start = text.rfind("<h2", 0, start)


end = text.find(
    "Community Review Network",
    start
)


if end == -1:
    raise SystemExit("Could not find Community Review Network")


end = text.rfind("<h2", start, end)


text = (
    text[:start]
    +
    text[end:]
)


path.write_text(text)

print("Removed old dashboard metrics")
