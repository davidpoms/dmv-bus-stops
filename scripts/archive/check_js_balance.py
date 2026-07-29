from pathlib import Path

text = Path("src/dashboard/static/dashboard.js").read_text()

stack = []
pairs = {
    ")": "(",
    "}": "{",
    "]": "["
}

for i, c in enumerate(text, 1):
    if c in "({[":
        stack.append((c, i))
    elif c in ")}]":
        if stack and stack[-1][0] == pairs[c]:
            stack.pop()
        else:
            print("Mismatch at character", i, repr(c))
            break

print("Remaining stack:")
for item in stack:
    print(item)
