from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()

old = '''
            return "remote";
'''

new = '''
            return "";
'''

if old not in text:
    raise Exception("Could not find default review mode")

text = text.replace(old, new, 1)

p.write_text(text)

print("Changed review mode default to blank")
