from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

blocks = text.split('if __name__ == "__main__":')

if len(blocks) <= 2:
    print("No duplicate app.run blocks found")
    raise SystemExit

# Keep everything before the first main block
# Remove all later main blocks
clean = blocks[0] + '\n\nif __name__ == "__main__":\n' + blocks[1].split(
    '\n',
    4
)[-1]

path.write_text(clean)

print("Removed duplicate app.run blocks")
