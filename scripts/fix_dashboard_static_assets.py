from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

source = ROOT / "src" / "dashboard" / "static"
target = ROOT / "static"

target.mkdir(exist_ok=True)

for filename in [
    "dashboard.js",
    "dashboard.css",
    "review.js",
]:
    src = source / filename
    dst = target / filename

    if src.exists():
        shutil.copy2(src, dst)
        print(f"Copied {src} -> {dst}")
    else:
        print(f"Missing: {src}")

print("\nStatic assets repaired.")
