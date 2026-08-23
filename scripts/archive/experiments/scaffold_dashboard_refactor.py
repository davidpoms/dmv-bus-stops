from pathlib import Path

BASE = Path("src/dashboard")

(BASE / "templates").mkdir(parents=True, exist_ok=True)
(BASE / "static").mkdir(parents=True, exist_ok=True)

(BASE / "templates" / "dashboard.html").write_text("""<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<title>DMV Bus Stop Dashboard</title>

<link rel="stylesheet"
href="https://unpkg.com/leaflet/dist/leaflet.css"/>

<link rel="stylesheet"
href="../static/dashboard.css"/>

<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>

</head>

<body>

<h1>DMV Bus Stop Improvement Dashboard</h1>

<label>Route Filter</label>

<select id="routeSelect">
<option value="">All Routes</option>
</select>

<div id="map"></div>

<script src="../static/dashboard.js"></script>

</body>
</html>
""")

(BASE / "static" / "dashboard.css").write_text("""body{
font-family:Arial,sans-serif;
margin:20px;
}

#map{
height:700px;
width:100%;
}
""")

(BASE / "static" / "dashboard.js").write_text(
'console.log("Dashboard JS loaded");\n'
)

print("Dashboard scaffold created.")
