from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find('if __name__ == "__main__":')

if start == -1:
    raise Exception("main block not found")

fixed = '''if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
'''

text = text[:start] + fixed

path.write_text(text)

print("Fixed app.run block")
