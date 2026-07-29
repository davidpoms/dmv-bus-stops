from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text=p.read_text()

old="""
    if (priority) {
        params.append("priority", priority);
    }
"""

new="""
    if (priority) {
        params.append("priority", priority);
    }


    if (actionFilter) {
        params.append(
            "action",
            actionFilter
        );
    }
"""

if old not in text:
    print("priority block not found")
    raise SystemExit(1)

text=text.replace(old,new,1)

p.write_text(text)

print("frontend action parameter added")
