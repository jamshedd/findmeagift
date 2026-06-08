# Gift Catalog — Image Fetcher Workflow

This bundle contains:

| File | Purpose |
|---|---|
| `gift_catalog.json` | The catalog. 51 categories, 5,100 items, attribute-tagged across 31 dimensions, with placeholder images. Every item now carries an `image.source` field (initial value `"procedural"`). |
| `fetch_catalog_images.py` | Replaces placeholders with real photos from Pexels (default), Pixabay, or Unsplash. Incremental by default — only touches items that aren't yet real. |
| `tag_placeholders.py` | One-time script that ensures every item has `image.source`. Already run against the catalog above, but here in case you regenerate. |


## Step 1 — Get a free API key

Pick one provider. Pexels is the recommended default (good search quality, simple API, generous free tier).

| Provider | Sign up | Free tier |
|---|---|---|
| **Pexels** | https://www.pexels.com/api/ | 200 req/hr, 20k/month |
| **Pixabay** | https://pixabay.com/api/docs/ | 100 req/min |
| **Unsplash** | https://unsplash.com/developers | 50/hr demo, 5,000/hr after free production approval |

Signup takes ~2 minutes for any of them.


## Step 2 — Install dependencies

```bash
pip install requests Pillow
```


## Step 3 — Set your API key as an env var

```bash
export PEXELS_API_KEY=your_key_here
# or PIXABAY_API_KEY=... / UNSPLASH_API_KEY=...
```


## Step 4 — Dry run first

See what the script would do without spending any API calls:

```bash
python fetch_catalog_images.py --input gift_catalog.json --dry-run
```


## Step 5 — Run

Default behaviour: update only items still on procedural placeholders or marked failed.

```bash
python fetch_catalog_images.py --input gift_catalog.json
```

The script saves progress every 50 successful fetches, so you can Ctrl-C and re-run anytime — it picks up where it left off.

For a small first batch:

```bash
python fetch_catalog_images.py --input gift_catalog.json --limit 50
```

For just a few categories:

```bash
python fetch_catalog_images.py --input gift_catalog.json --categories candles,fine_jewelry,pottery_ceramics
```

To use a different provider:

```bash
python fetch_catalog_images.py --input gift_catalog.json --provider pixabay
```


## Step 6 — Retry only the failures

After a run, some items may have `source: "failed"` (no search results, network error, image processing issue). Pick them up with:

```bash
python fetch_catalog_images.py --input gift_catalog.json --mode failed
```


## How "only update what's missing" works

Each item's `image.source` is one of:

| Value | Meaning |
|---|---|
| `procedural` | Original placeholder. Default fetch target. |
| `pexels`, `pixabay`, `unsplash` | Successfully replaced. Default mode skips these. |
| `failed` | Attempted but failed. Picked up by default mode and by `--mode failed`. |
| `user_supplied` | You added it manually. Skipped by default mode. |

If you want to force-replace everything, including successful real images:

```bash
python fetch_catalog_images.py --input gift_catalog.json --mode all
```


## Time and cost expectations

Each item needs roughly two API requests: one search, one image download. For 5,100 items that's ~10,200 requests.

| Provider | Free tier rate | Wall-clock at full rate |
|---|---|---|
| Pexels (200/hr) | 100 items/hr | ~50 hrs |
| Pixabay (100/min) | ~3,000 items/hr | ~1.5 hrs |
| Unsplash demo (50/hr) | 25 items/hr | ~200 hrs (request prod access) |

Pixabay is the fastest if you don't already have an Unsplash production key. Recommend starting with Pexels for quality and switching to Pixabay if the rate limit is a problem.

The script caches search results per category (5 URLs per search, rotated across ~20 items) so the actual API search count is closer to 250 searches total, not 5,100 — which keeps you well under the free tier.


## Tuning the queries

Search queries per category are defined in `fetch_catalog_images.py` near the top, in `CATEGORY_QUERIES`. Each category has a list of queries that get rotated across items in that category for visual variety. If you find images coming back generic or off-theme for a category, tweak that list and re-run with `--mode all --categories that_category_id`.


## Image processing

Downloaded images are center-cropped to square and resized to 600×600, then JPEG-encoded at quality 82 and base64-stored in `item.image.data`. Tune `IMAGE_SIZE` and `JPEG_QUALITY` constants near the top of the fetcher if you want smaller files or higher fidelity.


## What the schema looks like before and after

Before (placeholder):

```json
"image": {
  "format": "image/png",
  "encoding": "base64",
  "source": "procedural",
  "data": "iVBORw0KGgo..."
}
```

After (Pexels):

```json
"image": {
  "format": "image/jpeg",
  "encoding": "base64",
  "source": "pexels",
  "data": "/9j/4AAQSkZJ..."
}
```

Your DB import should accept either format/encoding pair. If your DB schema needs to know format/source, the fields are right there next to the data.
