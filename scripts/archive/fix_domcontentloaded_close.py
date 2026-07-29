from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
      }
  );

"""

new = """
      }
  });

"""

if old not in text:
    raise SystemExit("ending block not found")

text = text.replace(old, new, 1)

p.write_text(text)

print("fixed DOMContentLoaded closing")
