from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

old = """
        "routes": route_validation_metrics(),
    }
"""

new = """
        "routes": route_validation_metrics(),
        "consensus": consensus_progress_metrics(),
    }
"""

if old in text:
    text=text.replace(old,new,1)
    print("Added consensus metrics to dashboard bundle")
else:
    print("Bundle block not found")

p.write_text(text)
