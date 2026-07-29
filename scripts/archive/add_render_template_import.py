from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = "from flask import Flask, jsonify, send_from_directory, request"

new = "from flask import Flask, jsonify, send_from_directory, request, render_template"

if "render_template" in text.split("\n")[6]:
    print("render_template already imported")
    raise SystemExit

if old not in text:
    raise SystemExit("Could not find Flask import line")

text = text.replace(old, new)

path.write_text(text)

print("Added render_template import")
