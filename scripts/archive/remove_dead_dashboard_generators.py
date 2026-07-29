from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

start = text.index("    impact_list =")
end = text.index("    template = Template(")

text = text[:start] + text[end:]

p.write_text(text)

print("Removed old priority/impact generators")
