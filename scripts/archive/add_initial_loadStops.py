from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
    }
);



});
"""

new = """
    }
);


loadStops();


});
"""

if "loadStops();" not in text:
    text = text.replace(old, new)
    p.write_text(text)
    print("Added initial loadStops call")
else:
    print("loadStops already exists")
