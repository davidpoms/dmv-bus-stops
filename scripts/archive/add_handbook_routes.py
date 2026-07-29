from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

marker = "from flask import"

if "def community_handbook" in text:
    print("Handbook routes already exist")
    raise SystemExit


routes = """

@app.route("/handbook")
def community_handbook():

    from pathlib import Path
    import markdown

    path = Path("docs/DMV_Bus_Stop_Intelligence_Handbook.md")

    html = markdown.markdown(
        path.read_text(),
        extensions=["tables"]
    )

    return html



@app.route("/volunteer-handbook")
def volunteer_handbook():

    from pathlib import Path
    import markdown

    path = Path("docs/Volunteer_Review_Handbook.md")

    html = markdown.markdown(
        path.read_text(),
        extensions=["tables"]
    )

    return html


"""


# put before final app.run if present
if "if __name__ ==" in text:
    text = text.replace(
        "if __name__ ==",
        routes + "\n\nif __name__ =="
    )
else:
    text += routes


p.write_text(text)

print("Added handbook routes")
