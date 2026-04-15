"""
Reddit scraper for trending products.
Uses Reddit's free JSON API (no auth needed for public subreddits).
Targets product-focused subreddits used by shoppers and deal-hunters.
"""
import requests
import time
import random
import re

HEADERS = {
    "User-Agent": "DropshipTrends/1.0 (product research bot; https://github.com)",
    "Accept": "application/json",
}

SUBREDDITS = [
    ("shutupandtakemymoney", "Hot Products"),
    ("deals", "Deals"),
    ("BuyItForLife", "Quality Products"),
    ("Entrepreneur", "Business Trends"),
    ("ecommerce", "Ecommerce Trends"),
]

# Patterns that suggest a post is about a product
PRODUCT_PATTERNS = [
    r"\$[\d,.]+",  # price mention
    r"(?:review|unboxing|bought|purchase|order|shipping)",
    r"(?:amazon|ebay|aliexpress|walmart|etsy|shopify)",
    r"(?:discount|sale|deal|coupon|off)",
]


def _extract_price(text):
    """Try to extract a price from post text."""
    match = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
    return match.group(0) if match else "N/A"


def _is_product_post(title, text=""):
    """Check if post is likely about a product."""
    combined = (title + " " + text).lower()
    return any(re.search(p, combined, re.IGNORECASE) for p in PRODUCT_PATTERNS)


def get_trending_products():
    session = requests.Session()
    session.headers.update(HEADERS)
    products = []

    for subreddit, category in SUBREDDITS:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
        try:
            time.sleep(random.uniform(1, 2))
            response = session.get(url, timeout=15)

            if response.status_code != 200:
                print(f"  Reddit r/{subreddit}: HTTP {response.status_code}")
                continue

            data = response.json()
            posts = data.get("data", {}).get("children", [])
            count = 0

            for i, post in enumerate(posts):
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                text = post_data.get("selftext", "")
                score = post_data.get("score", 0)
                url_post = post_data.get("url", "")
                thumbnail = post_data.get("thumbnail", "")
                upvote_ratio = post_data.get("upvote_ratio", 0.5)

                # Skip low-effort posts
                if score < 10 or len(title) < 5:
                    continue

                # For r/shutupandtakemymoney and r/deals, most posts are products
                # For others, apply a filter
                if subreddit not in ("shutupandtakemymoney", "deals"):
                    if not _is_product_post(title, text):
                        continue

                # Clean thumbnail
                image = ""
                if thumbnail and thumbnail.startswith("http") and "thumbnail" not in thumbnail:
                    image = thumbnail

                price = _extract_price(title + " " + text)

                # Trend score: based on Reddit upvotes (capped and normalized)
                trend_score = min(int(score / 100), 50) + int(upvote_ratio * 20)

                products.append(
                    {
                        "id": f"reddit_{subreddit}_{i}",
                        "name": title[:120],
                        "price": price,
                        "image": image,
                        "url": url_post if url_post.startswith("http") else f"https://reddit.com{url_post}",
                        "source": "Reddit",
                        "category": category,
                        "position": i + 1,
                        "rank_change": f"{score} upvotes",
                        "score": trend_score,
                    }
                )
                count += 1

            print(f"  Reddit r/{subreddit}: {count} items")

        except Exception as e:
            print(f"  Reddit r/{subreddit} error: {e}")

    print(f"Reddit total: {len(products)} products")
    return products
