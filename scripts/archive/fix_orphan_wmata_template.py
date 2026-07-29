from pathlib import Path

p = Path("src/dashboard/static/review_info_loader.js")

text = p.read_text()

bad = """
                        ` 
                        :
                        ""
                    }


"""

if bad not in text:
    # handle whitespace variation
    bad = """
                        `
                        :
                        ""
                    }


"""

if bad not in text:
    raise Exception("Could not find orphan template block")

text = text.replace(
    bad,
    "",
    1
)

p.write_text(text)

print("Removed orphan WMATA template closing block")
