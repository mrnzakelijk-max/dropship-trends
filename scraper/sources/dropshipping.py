"""
Dedicated dropshipping communities scraper.
Targets subreddits where dropshippers discuss winning products.
Returns products with is_dropship=True and a supplier_url.
"""
import requests
import re
import time
import random

HEADERS = {
    "User-Agent": "DropshipTrends/1.0 (dropship research; https://github.com)",
    "Accept": "application/json",
}

SUBREDDITS = [
    ("dropship",           "Dropshipping"),
    ("dropshipping",       "Dropshipping"),
    ("AliExpressDropship", "AliExpress Dropship"),
    ("shopify",            "Shopify"),
    ("ecommerce",          "Ecommerce"),
]

SORT_MODES = ["hot", "top"]

PRICE_RE  = re.compile(r"\$[\d,]+(?:\.\d{2})?")
ALIEX_RE  = re.compile(r"aliexpress\.com/item/(\d+)", re.IGNORECASE)
SHOPIFY_RE = re.compile(r"https?://\S+\.myshopify\.com\S*", re.IGNORECASE)


def _extract_price(text):
    m = PRICE_RE.search(text)
    return m.group(0) if m else "N/A"


def _extract_aliexpress_url(text):
    """Pull a direct AliExpress product URL from post text if present."""
    m = ALIEX_RE.search(text)
    if m:
        return f"https://www.aliexpress.com/item/{m.group(1)}.html"
    # Also check for full URLs in text
    full = re.search(r"https?://(?:www\.)?aliexpress\.com/item/\d+\.html", text, re.IGNORECASE)
    return full.group(0) if full else ""


def _build_supplier_url(name):
    """Fallback: build AliExpress search URL from product name."""
    encoded = requests.utils.quote(name[:80])
    return f"https://www.aliexpress.com/wholesale?SearchText={encoded}&SortType=total_tranSqfm_desc"


def get_dropship_products():
    session = requests.Session()
    session.headers.update(HEADERS)
    products = []
    seen_titles = set()

    for subreddit, category in SUBREDDITS:
        for sort in SORT_MODES:
            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit=25&t=week"
            try:
                time.sleep(random.uniform(1.0, 2.0))
                resp = session.get(url, timeout=15)
                if resp.status_code != 200:
                    continue

                posts = resp.json().get("data", {}).get("children", [])

                for post in posts:
                    d = post.get("data", {})
                    title   = d.get("title", "").strip()
                    text    = d.get("selftext", "")
                    score   = d.get("score", 0)
                    ratio   = d.get("upvote_ratio", 0.5)
                    post_url = d.get("url", "")
                    thumb   = d.get("thumbnail", "")

                    if score < 5 or len(title) < 8:
                        continue

                    # Deduplicate
                    key = title.lower()[:60]
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)

                    combined = title + " " + text

                    # Find supplier URL (direct AliExpress link preferred)
                    supplier_url = _extract_aliexpress_url(combined)
                    if not supplier_url:
                        supplier_url = _build_supplier_url(title)

                    # Selling URL (where it's sold)
                    sell_url = post_url if post_url.startswith("http") else f"https://reddit.com{post_url}"

                    price = _extract_price(combined)
                    image = thumb if (thumb and thumb.startswith("http") and "external-preview" in thumb or
                                       thumb.startswith("https://preview.redd")) else ""

                    trend_score = min(int(score / 50), 40) + int(ratio * 20)

                    products.append({
                        "id": f"dropship_{subreddit}_{len(products)}",
                        "name": title[:120],
                        "price": price,
                        "image": image,
                        "url": sell_url,
                        "supplier_url": supplier_url,
                        "source": "Reddit Dropship",
                        "category": category,
                        "position": len(products) + 1,
                        "rank_change": f"{score} upvotes",
                        "score": trend_score,
                        "is_dropship": True,
                    })

            except Exception as e:
                print(f"  Dropship r/{subreddit}/{sort} error: {e}")

    print(f"Dropshipping communities total: {len(products)} products")
    return products
