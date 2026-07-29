from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

# Replace geography section again
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


    ward_list = "\n".join(
        f"""
        <tr>
            <td>Ward {x['dc_ward']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in dc_wards()
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

# restore template substitutions
text = text.replace(
    "anc_list=anc_list,",
    "anc_list=anc_list,\n        ward_list=ward_list,"
)

p.write_text(text)

print("Added both DC ward and ANC lists")
