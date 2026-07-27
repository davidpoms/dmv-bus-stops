from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
    query_db(
        """
        INSERT INTO stop_observations
'''

new = '''
    print("NORMALIZED REVIEW MODE:", data.get("review_mode"))
    print("FULL NORMALIZED DATA:", data)

    query_db(
        """
        INSERT INTO stop_observations
'''

if old not in text:
    raise Exception("Could not find INSERT start")

text = text.replace(old, new, 1)

p.write_text(text)

print("Added review mode debug")
