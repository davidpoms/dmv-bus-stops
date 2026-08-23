import requests

s = requests.Session()

for i in range(5):
    r = s.get(
        "http://localhost:8000/review/start?mode=route",
        allow_redirects=False,
    )
    print(r.status_code, r.headers.get("Location"))