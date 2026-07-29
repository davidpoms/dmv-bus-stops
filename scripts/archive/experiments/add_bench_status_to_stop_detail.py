from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    evidence = get_stop_evidence_summary(stop_id)


    return jsonify(
"""

new = """
    evidence = get_stop_evidence_summary(stop_id)

    bench_status = interpret_bench_status(evidence)


    return jsonify(
"""

if old not in text:
    raise Exception("Evidence injection point not found")

text = text.replace(old, new, 1)


old = """
            "evidence": evidence
        }
    )
"""

new = """
            "evidence": evidence,

            "bench_status": bench_status
        }
    )
"""

if old not in text:
    raise Exception("JSON response block not found")

text = text.replace(old, new, 1)

p.write_text(text)

print("Added bench status to stop detail")
