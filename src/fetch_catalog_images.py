#!/usr/bin/env python3
"""
fetch_catalog_images.py
-----------------------

Replace placeholder images in gift_catalog.json with real photos from a free
stock-photo API (Pexels, Pixabay, or Unsplash). All three allow commercial use;
each requires a free API key (signup is ~2 minutes).

QUICK START
-----------
    pip install requests Pillow

    # Pick ONE provider and get a free API key:
    #   Pexels:   https://www.pexels.com/api/        (recommended; 200 req/hr)
    #   Pixabay:  https://pixabay.com/api/docs/      (100 req/min)
    #   Unsplash: https://unsplash.com/developers    (50/hr demo, 5000/hr prod)

    export PEXELS_API_KEY=your_key_here              # or PIXABAY_API_KEY / UNSPLASH_API_KEY

    # Dry run to see what would happen:
    python fetch_catalog_images.py --dry-run

    # Default: update only items still showing procedural placeholders:
    python fetch_catalog_images.py

    # Update everything regardless (overwrites real images too):
    python fetch_catalog_images.py --mode all

    # Retry just the items that previously failed:
    python fetch_catalog_images.py --mode failed

    # Limit for testing:
    python fetch_catalog_images.py --limit 50

    # Restrict to a few categories:
    python fetch_catalog_images.py --categories fine_jewelry,candles,pottery_ceramics


HOW THE "ONLY UPDATE WHAT'S MISSING" MODE WORKS
-----------------------------------------------
Every item's image carries a `source` field:
    "procedural"     - the original placeholder
    "pexels"         - real photo successfully fetched from Pexels
    "pixabay"        - real photo from Pixabay
    "unsplash"       - real photo from Unsplash
    "user_supplied"  - you added it manually (script will leave these alone)
    "failed"         - we tried, couldn't get one (retryable)

Default mode ("placeholders") updates items where source is "procedural" or
"failed". So if you run the script, get interrupted, fix a network issue, and
re-run, it picks up where it left off. If you want to retry only the failures,
use --mode failed.


OUTPUT
------
Updates are written back to the same file (or --output path). Progress is
saved every 50 successful fetches so it's safe to Ctrl-C mid-run.


COSTS AND TIME
--------------
Pexels free tier: 200 requests/hour, 20,000/month. The script needs roughly
2 requests per item (search + image download), so 5,100 items = ~10,200
requests = ~50 hours of wall-clock at the 200/hr limit. In practice you'll
want to either:
  (a) run it overnight in chunks, or
  (b) request elevated Pexels access (free, just fill out a form), or
  (c) split across providers using --provider.
"""

import argparse
import base64
import io
import json
import os
import random
import sys
import time
from pathlib import Path

import requests
from PIL import Image

# ----------------------------------------------------------------------------
# Tuning knobs
# ----------------------------------------------------------------------------
IMAGE_SIZE = (600, 600)        # square output (cropped center, resized)
JPEG_QUALITY = 82               # 75-85 is a good range
SAVE_EVERY = 50                 # save JSON every N successful fetches
HTTP_TIMEOUT = 30               # seconds
RETRY_ON_TRANSIENT = 2          # retry failed network calls this many times
SLEEP_BETWEEN_ITEMS = 0.5       # baseline throttle; tightened per provider below

# Per-provider rate limiting (requests per minute we'll actually issue).
PROVIDER_RPM = {
    "pexels": 180,    # cap below 200/hr would be too slow; 180/min if you have prod access
    "pixabay": 90,
    "unsplash": 45,   # demo tier; raise if you have prod access
}


# ----------------------------------------------------------------------------
# Category → search queries
# Each item picks a query from its category's list based on its item id, so
# items within the same category get visual variety.
# ----------------------------------------------------------------------------
CATEGORY_QUERIES = {
    "fine_jewelry":            ["gold necklace", "silver pendant", "diamond ring", "pearl earrings", "fine jewelry"],
    "statement_jewelry":       ["statement necklace", "bold earrings", "chunky bracelet", "costume jewelry"],
    "mens_jewelry":            ["mens cufflinks", "leather bracelet men", "signet ring", "mens watch detail"],
    "wall_art_prints":         ["wall art print", "minimal art poster", "framed print", "abstract art print"],
    "original_paintings":      ["abstract painting", "oil painting canvas", "watercolor painting", "modern painting"],
    "photography_prints":      ["black white photography", "landscape photograph", "fine art photo"],
    "sculptures_3d":           ["sculpture art", "ceramic sculpture", "modern sculpture", "art object"],
    "candles":                 ["soy candle", "scented candle", "candle jar", "luxury candle"],
    "bath_body":               ["bath products", "body scrub", "bath salt", "body oil bottle"],
    "soap_bars":               ["handmade soap", "soap bar artisan", "natural soap"],
    "perfume_fragrance":       ["perfume bottle", "fragrance bottle", "cologne", "essential oil bottle"],
    "pottery_ceramics":        ["pottery vase", "ceramic bowl", "handmade ceramic", "stoneware pottery"],
    "glassware":               ["wine glass set", "glass tumbler", "crystal glass", "hand blown glass"],
    "mugs_drinkware":          ["ceramic mug", "coffee mug handmade", "stoneware mug", "tea cup"],
    "kitchen_tools":           ["wooden spoon", "kitchen utensils wood", "cooking tools", "salad servers"],
    "cutting_boards":          ["wooden cutting board", "charcuterie board", "wood serving board"],
    "aprons_linens":           ["linen apron", "tea towel", "linen kitchen", "table linens"],
    "tea_coffee_accessories":  ["pour over coffee", "tea infuser", "coffee accessories", "matcha set"],
    "wine_bar":                ["cocktail shaker", "wine decanter", "bar accessories", "whiskey glasses"],
    "stationery_cards":        ["greeting card", "stationery set", "letterpress card", "paper goods"],
    "journals_notebooks":      ["leather journal", "notebook", "writing journal", "linen notebook"],
    "calendars_planners":      ["planner notebook", "wall calendar", "weekly planner", "desk calendar"],
    "desk_accessories":        ["desk organizer", "pen holder", "minimal desk", "workspace accessories"],
    "home_decor":              ["home decor object", "decorative object", "sculptural decor", "minimal home decor"],
    "wall_hangings":           ["macrame wall hanging", "tapestry wall", "woven wall art", "fiber art"],
    "throw_pillows":           ["throw pillow", "decorative cushion", "linen pillow", "boho pillow"],
    "throw_blankets":          ["throw blanket", "wool throw", "knit blanket", "cozy blanket"],
    "rugs_mats":               ["area rug", "boho rug", "woven rug", "neutral rug"],
    "lamps_lighting":          ["table lamp", "modern lamp", "ceramic lamp", "pendant light"],
    "mirrors":                 ["wall mirror", "round mirror", "decorative mirror", "vintage mirror"],
    "clocks":                  ["wall clock", "modern clock", "wooden clock", "minimal clock"],
    "garden_outdoor":          ["garden tools", "watering can", "garden trowel", "pruning shears"],
    "planters":                ["ceramic planter", "terracotta pot", "modern planter", "plant pot"],
    "pet_accessories":         ["dog collar leather", "pet bowl", "cat toy", "pet bed"],
    "baby_toddler":            ["baby toys wooden", "baby blanket", "wooden rattle", "baby accessories"],
    "kids_toys":               ["wooden toys", "kids puzzle", "stuffed animal", "wooden blocks"],
    "nursery_decor":           ["nursery decor", "nursery art", "baby room decor", "kids room art"],
    "wedding":                 ["wedding decor", "wedding favor", "wedding signage", "wedding details"],
    "anniversary":             ["anniversary gift", "personalized frame", "couple gift", "love gift"],
    "mens_apparel":            ["mens linen shirt", "mens sweater", "wool cardigan men", "mens clothing"],
    "womens_apparel":          ["linen dress", "knit cardigan women", "silk camisole", "womens clothing"],
    "hats_beanies":            ["knit beanie", "wool hat", "felt hat", "winter hat"],
    "scarves_wraps":           ["cashmere scarf", "wool wrap", "silk scarf", "neutral scarf"],
    "socks":                   ["wool socks", "knit socks", "cozy socks"],
    "bags_purses":             ["leather tote bag", "crossbody bag", "leather handbag", "leather purse"],
    "wallets_leather":         ["leather wallet", "card holder leather", "minimal wallet", "leather goods"],
    "watches":                 ["minimal watch", "leather strap watch", "mens watch", "wrist watch"],
    "knitwear_crochet":        ["knit sweater", "hand knit cardigan", "crochet throw", "wool knitwear"],
    "embroidery":              ["embroidery hoop art", "embroidered fabric", "cross stitch", "needlework"],
    "resin_crystal":           ["resin coaster", "resin art", "crystal cluster", "geode"],
    "edible_gifts":            ["artisan chocolate", "spice jars", "hot sauce", "honey jar"],
}


# ----------------------------------------------------------------------------
# Provider implementations
# Each returns a list of image URLs given (query, count, api_key).
# ----------------------------------------------------------------------------

def search_pexels(query, count, api_key):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": max(count, 5), "orientation": "square"}
    r = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    photos = r.json().get("photos", [])
    urls = []
    for p in photos:
        src = p.get("src", {})
        u = src.get("large") or src.get("medium") or src.get("original")
        if u:
            urls.append(u)
        if len(urls) >= count:
            break
    return urls


def search_pixabay(query, count, api_key):
    url = "https://pixabay.com/api/"
    params = {"key": api_key, "q": query, "per_page": max(count, 3), "image_type": "photo", "safesearch": "true"}
    r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    urls = []
    for h in hits:
        u = h.get("largeImageURL") or h.get("webformatURL")
        if u:
            urls.append(u)
        if len(urls) >= count:
            break
    return urls


def search_unsplash(query, count, api_key):
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {api_key}"}
    params = {"query": query, "per_page": max(count, 5), "orientation": "squarish"}
    r = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    results = r.json().get("results", [])
    urls = []
    for ph in results:
        u = ph.get("urls", {}).get("regular") or ph.get("urls", {}).get("small")
        if u:
            urls.append(u)
        if len(urls) >= count:
            break
    return urls


PROVIDERS = {
    "pexels": search_pexels,
    "pixabay": search_pixabay,
    "unsplash": search_unsplash,
}


# ----------------------------------------------------------------------------
# Image processing
# ----------------------------------------------------------------------------

def download_image_bytes(url):
    """Fetch raw image bytes from a CDN URL (no auth)."""
    last_err = None
    for attempt in range(RETRY_ON_TRANSIENT + 1):
        try:
            r = requests.get(url, timeout=HTTP_TIMEOUT, stream=True)
            r.raise_for_status()
            return r.content
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)
    raise last_err


def process_image(raw_bytes):
    """Open, center-crop to square, resize, JPEG-encode. Returns JPEG bytes."""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize(IMAGE_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


# ----------------------------------------------------------------------------
# Query building per item
# ----------------------------------------------------------------------------

def query_for_item(item):
    cat_id = item["category_id"]
    queries = CATEGORY_QUERIES.get(cat_id)
    if not queries:
        return item["category_name"].lower()
    # Pick deterministically based on item index so items in a category get spread.
    idx = int(item["id"].split("_")[-1]) % len(queries)
    return queries[idx]


# ----------------------------------------------------------------------------
# Catalog IO
# ----------------------------------------------------------------------------

def load_catalog(path):
    with open(path) as f:
        return json.load(f)


def save_catalog(catalog, path):
    tmp = Path(str(path) + ".tmp")
    with tmp.open("w") as f:
        json.dump(catalog, f, separators=(",", ":"))
    tmp.replace(path)


def normalize_source(item):
    """Ensure image.source exists; legacy items default to 'procedural'."""
    img = item.setdefault("image", {})
    if "source" not in img:
        img["source"] = "procedural"


# ----------------------------------------------------------------------------
# Main update loop
# ----------------------------------------------------------------------------

def select_candidates(items, mode, cat_filter):
    out = []
    for it in items:
        normalize_source(it)
        src = it["image"]["source"]
        if cat_filter and it["category_id"] not in cat_filter:
            continue
        if mode == "placeholders":
            if src in ("procedural", "failed"):
                out.append(it)
        elif mode == "failed":
            if src == "failed":
                out.append(it)
        elif mode == "all":
            out.append(it)
    return out


def update_item(item, provider, api_key, _url_cache_by_cat):
    """Fetch a real image for `item`. Mutates `item` in-place. Returns True on success."""
    cat_id = item["category_id"]
    # Try to reuse a per-category URL cache so we don't hammer the API on every item.
    # Each call to the search API yields up to ~5 URLs; we round-robin among them
    # for items in the same category.
    cache = _url_cache_by_cat.setdefault(cat_id, {"urls": [], "cursor": 0})
    if not cache["urls"]:
        query = query_for_item(item)
        try:
            urls = PROVIDERS[provider](query, 5, api_key)
        except Exception as e:
            print(f"  ! Search failed ({provider}, '{query}'): {e}", file=sys.stderr)
            item["image"]["source"] = "failed"
            return False
        if not urls:
            print(f"  ! No results for query '{query}'", file=sys.stderr)
            item["image"]["source"] = "failed"
            return False
        random.shuffle(urls)  # mix within a query batch
        cache["urls"] = urls
        cache["cursor"] = 0

    url = cache["urls"][cache["cursor"] % len(cache["urls"])]
    cache["cursor"] += 1
    # When cursor exceeds list length, the next item in this category will
    # trigger a fresh search (because we don't reset cache; we just rotate).
    # To force fresh searches periodically, drop cache when cursor hits len:
    if cache["cursor"] >= len(cache["urls"]) * 4:
        cache["urls"] = []

    try:
        raw = download_image_bytes(url)
        processed = process_image(raw)
    except Exception as e:
        print(f"  ! Download/process failed for {url}: {e}", file=sys.stderr)
        item["image"]["source"] = "failed"
        return False

    item["image"] = {
        "format": "image/jpeg",
        "encoding": "base64",
        "source": provider,
        "data": base64.b64encode(processed).decode("ascii"),
    }
    return True


def main():
    parser = argparse.ArgumentParser(description="Replace placeholder images in gift_catalog.json with real photos.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__)
    parser.add_argument("--input", default="gift_catalog.json", help="Path to catalog JSON (default: ./gift_catalog.json)")
    parser.add_argument("--output", default=None, help="Output path (default: overwrite input)")
    parser.add_argument("--provider", choices=list(PROVIDERS), default="pexels", help="Which API to use (default: pexels)")
    parser.add_argument("--api-key", default=None, help="API key (or set PEXELS_API_KEY / PIXABAY_API_KEY / UNSPLASH_API_KEY env var)")
    parser.add_argument("--mode", choices=["placeholders", "failed", "all"], default="placeholders",
                        help="placeholders (default): items with source=procedural or failed. failed: only retry failed items. all: every item.")
    parser.add_argument("--categories", default=None, help="Comma-separated category_ids to restrict to")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N successful updates")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated, change nothing")
    args = parser.parse_args()

    # Resolve API key from --api-key, then env, then exit.
    env_keys = {"pexels": "PEXELS_API_KEY", "pixabay": "PIXABAY_API_KEY", "unsplash": "UNSPLASH_API_KEY"}
    api_key = args.api_key or os.environ.get(env_keys[args.provider])
    if not api_key and not args.dry_run:
        sys.exit(f"ERROR: API key required. Set --api-key or {env_keys[args.provider]} env var.")

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path
    if not input_path.exists():
        sys.exit(f"ERROR: input file not found: {input_path}")

    print(f"Loading {input_path} ...")
    catalog = load_catalog(input_path)

    cat_filter = set(args.categories.split(",")) if args.categories else None
    candidates = select_candidates(catalog["items"], args.mode, cat_filter)

    print(f"Catalog: {len(catalog['items'])} items total. Eligible under mode='{args.mode}': {len(candidates)}.")
    if not candidates:
        print("Nothing to do.")
        return

    if args.dry_run:
        print("\nDry run. First 10 candidates that would be updated:")
        for c in candidates[:10]:
            print(f"  {c['id']}  [{c['category_id']:25s}] {c['name'][:60]:60s}  source={c['image']['source']}")
        print(f"\nFull queue size: {len(candidates)}. Re-run without --dry-run to execute.")
        return

    print(f"Provider: {args.provider}.  Mode: {args.mode}.  Output: {output_path}")
    rpm = PROVIDER_RPM[args.provider]
    sleep_s = max(SLEEP_BETWEEN_ITEMS, 60.0 / rpm)
    print(f"Throttle: ~{rpm} req/min  ({sleep_s:.2f}s between items)")

    successes, failures = 0, 0
    url_cache = {}
    t_start = time.time()
    try:
        for i, item in enumerate(candidates, 1):
            if args.limit and successes >= args.limit:
                print(f"Reached --limit {args.limit}.")
                break
            print(f"[{i}/{len(candidates)}] {item['id']} {item['name'][:55]:55s}", end=" ... ", flush=True)
            ok = update_item(item, args.provider, api_key, url_cache)
            if ok:
                successes += 1
                print("OK")
            else:
                failures += 1
                print("FAILED")
            if successes and successes % SAVE_EVERY == 0:
                save_catalog(catalog, output_path)
                elapsed = time.time() - t_start
                rate = successes / max(elapsed, 1) * 60
                print(f"  > checkpoint: {successes} updates saved. {rate:.1f}/min so far.")
            time.sleep(sleep_s)
    except KeyboardInterrupt:
        print("\nInterrupted. Saving progress before exit ...")

    save_catalog(catalog, output_path)
    elapsed = time.time() - t_start
    print(f"\nDone. Updated {successes}, failed {failures}, in {elapsed:.0f}s ({successes / max(elapsed/60, 0.01):.1f}/min).")
    print(f"Output: {output_path}")
    if failures:
        print(f"Tip: re-run with --mode failed to retry the {failures} failures only.")


if __name__ == "__main__":
    main()
