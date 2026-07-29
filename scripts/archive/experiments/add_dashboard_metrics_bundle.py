from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def dashboard_metrics():
    return {
        "verification": community_verification_metrics(),
        "coverage": verification_coverage(),
        "benches": bench_metrics(),
        "routes": route_validation_metrics(),
    }

'''

if "def dashboard_metrics" not in text:
    p.write_text(text + addition)

print("Added dashboard metrics bundle")
