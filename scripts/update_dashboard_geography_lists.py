from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

start = text.index("    county_list = ")

end = text.index("    template = Template", start)

new_block = r'''
    county_list = "\n".join(
        f"""
        <tr>
            <td>{x['state']}</td>
            <td>{x['county']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in counties()
    )


    municipality_list = "\n".join(
        f"""
        <tr>
            <td>{x['state']}</td>
            <td>{x['county']}</td>
            <td>{x['municipality']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in municipalities()
    )


    anc_list = "\n".join(
        f"""
        <tr>
            <td>{x['dc_anc']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in dc_ancs()
    )


'''

text = text[:start] + new_block + text[end:]

# replace template variable
text = text.replace(
    "ward_list=ward_list,",
    "anc_list=anc_list,"
)

p.write_text(text)

print("Updated geography list generation")
