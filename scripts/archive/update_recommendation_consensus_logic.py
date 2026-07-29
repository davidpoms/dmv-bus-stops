from pathlib import Path

p = Path("src/assessment/generate_improvement_recommendations.py")

text = p.read_text()

old1 = """
        if opportunity_score >= 70 and not osm_bench:
"""

new1 = """
        if (
            opportunity_score >= 70
            and not osm_bench
            and consensus_bench != 1
        ):
"""

if old1 not in text:
    print("Bench condition not found")
    raise SystemExit

text = text.replace(old1, new1)


old2 = """
        if opportunity_score >= 80 and not osm_shelter:
"""

new2 = """
        if (
            opportunity_score >= 80
            and not osm_shelter
            and consensus_shelter != 1
        ):
"""

if old2 not in text:
    print("Shelter condition not found")
    raise SystemExit

text = text.replace(old2, new2)


p.write_text(text)

print("Recommendation consensus logic updated")
