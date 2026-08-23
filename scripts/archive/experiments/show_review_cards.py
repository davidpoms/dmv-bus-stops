from pathlib import Path

data = Path(
    "src/dashboard/templates/dashboard.html"
).read_text(encoding="utf-8")


start = data.find('<div class="review-options">')
end = data.find('<div class="card map-filter-card">')


print(data[start:end])