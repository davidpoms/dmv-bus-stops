from pathlib import Path

p = Path("scripts/build_stop_consensus.py")

text = p.read_text()

if 'ada_pct = agreement' in text:
    print("ada_pct already exists")
    raise SystemExit

old = '''    feasible_pct = agreement(
        "bench_feasible"
    )


    confidence = max(
        bench_pct,
        shelter_pct,
        feasible_pct
    )
'''

new = '''    feasible_pct = agreement(
        "bench_feasible"
    )

    ada_pct = agreement(
        "ada_clearance_possible"
    )


    confidence = max(
        bench_pct,
        shelter_pct,
        feasible_pct,
        ada_pct
    )
'''

if old not in text:
    print("Target block not found")
    raise SystemExit

text = text.replace(old,new)

p.write_text(text)

print("ADA consensus calculation added")
