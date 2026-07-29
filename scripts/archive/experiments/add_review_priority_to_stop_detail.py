from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    bench_status = interpret_bench_status(evidence)


    return jsonify(
"""

new = """
    bench_status = interpret_bench_status(evidence)

    review_priority = interpret_review_priority(
        evidence,
        bench_status
    )


    return jsonify(
"""

if old not in text:
    raise Exception("Bench status block not found")

text = text.replace(old, new, 1)


old = """
            "bench_status": bench_status
"""

new = """
            "bench_status": bench_status,

            "review_priority": review_priority
"""

if old not in text:
    raise Exception("Bench status response field not found")

text = text.replace(old, new, 1)

p.write_text(text)

print("Added review priority")
