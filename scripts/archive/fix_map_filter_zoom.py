from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/dashboard/static/dashboard.js")

backup = path.with_name(
    f"dashboard.js.before_filter_zoom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy2(path, backup)

print("Backup:")
print(backup)


text = path.read_text(encoding="utf-8")


if "L.featureGroup(markers).getBounds()" in text:
    print("fitBounds already added.")
    exit()


# Find the marker loop
start = text.find(
    "data.features.forEach("
)

if start == -1:
    raise SystemExit("Could not find data.features.forEach")


# Find the end of that forEach block.
# We look for the closing pattern before the next major section.
end_search = text.find(
    "\n        );",
    start
)

if end_search == -1:
    raise SystemExit("Could not find end of marker loop")


insert_at = end_search + len("\n        );")


addition = """



        if(markers.length){

            map.fitBounds(
                L.featureGroup(markers).getBounds()
            );

        }

"""


text = (
    text[:insert_at]
    + addition
    + text[insert_at:]
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Added map fitBounds after marker loading.")
print(path)