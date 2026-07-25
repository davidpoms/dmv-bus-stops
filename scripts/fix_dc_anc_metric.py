from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

start = text.index("def dc_ancs():")

# remove old broken function (it is currently the last geography function)
end = text.find("\n\ndef ", start + 5)

if end == -1:
    end = len(text)

text = text[:start] + text[end:]

addition = r'''

def dc_ancs():
    return query(
        """
        SELECT
            dc_anc,
            stop_count
        FROM dc_anc_summary
        ORDER BY dc_anc
        """
    )

'''

text += addition

p.write_text(text)

print("Fixed DC ANC dashboard metric")
