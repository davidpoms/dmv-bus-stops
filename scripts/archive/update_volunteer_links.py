from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

text = text.replace(
    '/dashboard?review=opportunity',
    '/review/start?mode=opportunity'
)

text = text.replace(
    '/dashboard?review=route',
    '/review/start?mode=route'
)

text = text.replace(
    '/dashboard?review=nearby',
    '/review/start?mode=nearby'
)

p.write_text(text)

print("Volunteer pathways connected")
