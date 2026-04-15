"""
Amazon Movers & Shakers scraper.
Fetches products with the biggest sales rank jumps in the past 24 hours.
"""
import cloudscraper
from bs4 import BeautifulSoup
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

CATEGORIES = [
    ("Electronics", "electronics"),
    ("Kitchen", "kitchen"),
    ("Toys", "toys-and-games"),
    ("Beauty", "beauty"),
    ("Health", "hpc"),
    ("Sports", "sporting-goods"),
    ("Home", "home-garden"),
    ("Clothing", "apparel"),
    ("Pet Supplies", "pet-supplies"),
    ("Office", "office-products"),
]


def get_trending_products():
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    products = []

    for category_name, slug in CATEGORIES:
        url = f"https://www.amazon.com/gp/movers-and-shakers/{slug}"
        try:
            time.sleep(random.uniform(3, 6))
            response = scraper.get(url, headers=HEADERS, timeout=20)

            if response.status_code != 200:
                print(f"  Amazon {category_name}: HTTP {response.status_code}")
                continue

            soup = BeautifulSoup(response.content, "lxml")

            # Try multiple container selectors (Amazon changes these regularly)
            items = (
                soup.select("div[id^='zg-item']")
                or soup.select(".zg-item-immersion")
                or soup.select("li.zg-item-immersion")
                or soup.select(".p13n-sc-uncoverable-faceout")
            )

            for i, item in enumerate(items[:10]):
                # Name — try several selectors
                name = None
                for sel in [
                    ".p13n-sc-truncate-desktop-type2",
                    "._cDEzb_p13n-sc-css-line-clamp-3_g3dy1",
                    ".a-size-small.a-link-normal",
                    "[class*='line-clamp']",
                ]:
                    el = item.select_one(sel)
                    if el:
                        name = el.get_text(strip=True)
                        break

                if not name or len(name) < 3:
                    continue

                # Price
                price_el = item.select_one(".p13n-sc-price") or item.select_one(
                    ".a-price .a-offscreen"
                )
                price = price_el.get_text(strip=True) if price_el else "N/A"

                # Image
                img_el = (
                    item.select_one("img.p13n-product-image-desktop")
                    or item.select_one("img[data-src]")
                    or item.select_one("img")
                )
                image = ""
                if img_el:
                    image = img_el.get("src") or img_el.get("data-src") or ""

                # Link
                link_el = item.select_one("a.a-link-normal[href]")
                product_url = ""
                if link_el:
                    href = link_el.get("href", "")
                    product_url = (
                        "https://www.amazon.com" + href
                        if href.startswith("/")
                        else href
                    )

                # Rank change badge (e.g. "#1 Most Gifted")
                rank_el = item.select_one(".zg-bdg-text") or item.select_one(
                    ".zg-badge-text"
                )
                rank_text = rank_el.get_text(strip=True) if rank_el else ""

                products.append(
                    {
                        "id": f"amazon_{slug}_{i}",
                        "name": name[:120],
                        "price": price,
                        "image": image,
                        "url": product_url,
                        "source": "Amazon",
                        "category": category_name,
                        "position": i + 1,
                        "rank_change": rank_text,
                        "score": max(10 - i, 1) * 10,
                    }
                )

            print(f"  Amazon {category_name}: {len([p for p in products if p['category'] == category_name])} items")

        except Exception as e:
            print(f"  Amazon {category_name} error: {e}")
            continue

    print(f"Amazon total: {len(products)} products")
    return products
