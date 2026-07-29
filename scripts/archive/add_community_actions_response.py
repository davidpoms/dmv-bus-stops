from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = '''
                "community_project": {

                    "status":
                        "active"
                        if installed_projects
                        else
                        "none",

                    "improvements":
                        installed_projects
                }

'''


new = '''
                "community_project": {

                    "status":
                        "active"
                        if installed_projects
                        else
                        "none",

                    "improvements":
                        installed_projects
                },


                "community_action": [

                    {
                        "status": row[0],
                        "type": row[1],
                        "steward": row[2],
                        "installed_date": row[3],
                        "notes": row[4]
                    }

                    for row in community_actions
                ]

'''


if old not in text:
    print("community project response block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new,
    1
)


p.write_text(text)

print("community actions response added")
