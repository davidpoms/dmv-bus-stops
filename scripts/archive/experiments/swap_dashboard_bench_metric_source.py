from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

text = text.replace(
    '"benches": bench_metrics(),',
    '"benches": stop_level_bench_metrics(),'
)

p.write_text(text)

print("Swapped dashboard bench metrics source")
