from pathlib import Path

p = Path("src/dashboard/templates/review.html")

text = p.read_text()


old = """
<div id="stopInfo">
Loading stop information...
</div>
"""


new = """
<div id="stopInfo">

<h3>
{{ stop_info.name }}
</h3>

<p>
<strong>Stop ID:</strong>
{{ stop_info.id }}
</p>

<p>
<strong>Coordinates:</strong>
{{ stop_info.latitude }},
{{ stop_info.longitude }}
</p>

<p>
<strong>State:</strong>
{{ stop_info.state }}
</p>

{% if stop_info.ward %}
<p>
<strong>Ward:</strong>
{{ stop_info.ward }}
</p>
{% endif %}

{% if stop_info.anc %}
<p>
<strong>ANC:</strong>
{{ stop_info.anc }}
</p>
{% endif %}

{% if stop_info.county %}
<p>
<strong>County:</strong>
{{ stop_info.county }}
</p>
{% endif %}

{% if stop_info.municipality %}
<p>
<strong>Municipality:</strong>
{{ stop_info.municipality }}
</p>
{% endif %}

</div>
"""


if old not in text:
    raise Exception("Could not find stopInfo placeholder")


text = text.replace(old,new)

p.write_text(text)

print("Updated review template geography display")
