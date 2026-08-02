from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


start = text.find('                    "queued":')

end = text.find(
    '                    "osm":',
    start
)

if start == -1 or end == -1:
    raise Exception("Could not find pipeline review block")


replacement = '''                    "queued":
                        count("""
                        SELECT COUNT(*)
                        FROM review_queue
                        WHERE physical_stop_id IN ({})
                        AND review_status = 'pending'
                        """),

                    "reviewed":
                        count("""
                        SELECT COUNT(DISTINCT physical_stop_id)
                        FROM stop_observations
                        WHERE physical_stop_id IN ({})
                        """),

                    "consensus":
                        count("""
                        SELECT COUNT(DISTINCT stop_id)
                        FROM stop_consensus
                        WHERE stop_id IN ({})
                        """),

'''

text = (
    text[:start]
    + replacement
    + text[end:]
)


path.write_text(text, encoding="utf-8")

print("Patched pipeline geography fields")