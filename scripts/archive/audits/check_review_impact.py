import requests
import json

data = requests.get(
    "http://localhost:8000/review/2333/info"
).json()

print(json.dumps(
    data.get("impact_summary"),
    indent=2
))