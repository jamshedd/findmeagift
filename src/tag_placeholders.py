"""One-time: add image.source='procedural' to every item in the catalog.

The fetcher script uses image.source to decide which items still need real
photos. Items with source='procedural' are placeholder; once Pexels/Unsplash
fetches succeed, source flips to 'pexels' or similar.

Safe to re-run.
"""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/outputs/gift_catalog.json")
with path.open() as f:
    catalog = json.load(f)

changed = 0
for item in catalog["items"]:
    img = item["image"]
    if "source" not in img:
        img["source"] = "procedural"
        changed += 1

with path.open("w") as f:
    json.dump(catalog, f, separators=(",", ":"))

print(f"Tagged {changed} items with source='procedural' (out of {len(catalog['items'])}).")
