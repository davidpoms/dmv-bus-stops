from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """
                    "stop_id": row["physical_stop_id"],
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "type": row["recommendation_type"],
                    "priority": row["priority"],
                    "confidence": row["confidence"],
                    "reasons": json.loads(row["reasons"])
                        if row["reasons"]
                        else [],
                    "evidence": json.loads(row["evidence"])
                        if row["evidence"]
                        else {}
"""

new = """
                    "stop_id": row["physical_stop_id"],
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "location_name": row["location_name"],
                    "priority_rank": row["priority_rank"],
                    "opportunity_score": row["opportunity_score"],
                    "review_status": row["review_status"],
                    "consensus_status": row["consensus_status"]
"""

if old not in text:
    raise Exception("Could not find old response block")

text = text.replace(old, new)

path.write_text(text)

print("Patched API review queue response")