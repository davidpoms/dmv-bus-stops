from pathlib import Path

p = Path("scripts/build_stop_consensus.py")

text = p.read_text()

if "ada_pct" in text:
    print("ADA consensus already added.")
    raise SystemExit


text = text.replace(
"""
    feasible_pct = agreement(
        "bench_feasible"
    )

    confidence = max(
        bench_pct,
        shelter_pct,
        feasible_pct
    )
""",
"""
    feasible_pct = agreement(
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
"""
)


text = text.replace(
"""
            bench_feasible,
            confidence,
            consensus_status
""",
"""
            bench_feasible,
            ada_accessible,
            confidence,
            consensus_status
"""
)


text = text.replace(
"""
            feasible_pct >= AGREEMENT_THRESHOLD,
            confidence,
            "verified"
""",
"""
            feasible_pct >= AGREEMENT_THRESHOLD,
            ada_pct >= AGREEMENT_THRESHOLD,
            confidence,
            "verified"
"""
)


p.write_text(text)

print("ADA consensus added.")
