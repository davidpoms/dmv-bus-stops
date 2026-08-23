from pathlib import Path

p = Path("src/dashboard/templates/survey.html")

p.write_text("""
<!DOCTYPE html>
<html>

<head>

<title>Bus Stop Review</title>

<style>

body {
    font-family: Arial, sans-serif;
    margin: 30px;
}

.container {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:30px;
}

.panel {
    border:1px solid #ccc;
    padding:20px;
    border-radius:8px;
}

label {
    display:block;
    margin-top:15px;
}

textarea {
    width:100%;
    height:100px;
}

button {
    margin-top:20px;
    padding:10px 20px;
    font-size:16px;
}

</style>

</head>


<body>


<h1>
Bus Stop Review
</h1>


<div id="review">
Loading...
</div>


<script src="/static/survey.js"></script>


</body>

</html>
""")

print("Created survey template")
