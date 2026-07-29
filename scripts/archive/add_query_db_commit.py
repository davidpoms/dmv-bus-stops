from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """    cursor.execute(sql, params)

    rows = cursor.fetchall()

    conn.close()

    return rows
"""

new = """    cursor.execute(sql, params)

    conn.commit()

    rows = cursor.fetchall()

    conn.close()

    return rows
"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print("Added commit to query_db")
else:
    print("Could not find query_db block")
