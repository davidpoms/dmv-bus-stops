from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

start = text.find('<div id="validationPanel">')

if start == -1:
    raise SystemExit("validation panel missing")

end = text.find('</div>', start)

# close nested validationList container
end = text.find('</div>', end+6)+6

text = text[:start] + text[end:]

p.write_text(text)

print("Removed validation panel")
