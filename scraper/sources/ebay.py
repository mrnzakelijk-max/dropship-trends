"""
eBay trending deals scraper.
Scrapes eBay's trending/deals pages for popular products.
"""
import requests
from bs4 import BeautifulSoup
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}

PAGES = [
    ("Trending", "https://www.ebay.com/deals/trending"),
    ("Electronics", "https://www.ebay.com/deals/electronics"),
    ("Home & Garden", "https://www.ebay.com/deals/home-garden"),
    ("Fashion", "https://www.ebay.com/deals/fashion"),
    ("Sports", "https://www.ebay.com/deals/sports"),
]


def _parse_page(html, category, offset=0):
    """Parse product tiles from an eBay deals page."""
    soup = BeautifulSoup(html, "lxml")
    items = (
        soup.select(".dne-itemtile")
        or soup.select("[class*='itemtile']")
        or soup.select(".s-item")
    )
    products = []

    for i, item in enumerate(items[:15]):
        # Name
        name_el = (
            item.select_one(".dne-itemtile-detail h3")
            or item.select_one(".itemtile-title")
            or item.select_one(".s-item__title")
            or item.select_one("h3")
        )
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if name.lower() in ("shop on ebay",) or len(name) < 3:
            continue

        # Price
        price_el = (
            item.select_one(".dne-itemtile-price")
            or item.select_one(".s-item__price")
            or item.select_one("[class*='price']")
        )
        price = price_el.get_text(strip=True) if price_el else "N/A"

        # Image
        img_el = item.select_one("img")
        image = ""
        if img_el:
            image = img_el.get("src") or img_el.get("data-src") or ""

        # Link
        link_el = item.select_one("a")
        product_url = link_el.get("href", "") if link_el else ""

        products.append(
            {
                "id": f"ebay_{category.lower().replace(' ', '_')}_{offset + i}",
                "name": name[:120],
                "price": price,
                "image": image,
                "url": product_url,
                "source": "eBay",
                "category": category,
                "position": offset + i + 1,
                "rank_change": "",
                "score": max(15 - i, 1) * 4,
            }
        )
    return products


def get_trending_products():
    session = requests.Session()
    session.headers.update(HEADERS)
    products = []

    for category, url in PAGES:
        try:
            time.sleep(random.uniform(1, 3))
            response = session.get(url, timeout=15)
            if response.status_code == 200:
                page_products = _parse_page(response.text, category, len(products))
                products.extend(page_products)
                print(f"  eBay {category}: {len(page_products)} items")
            else:
                print(f"  eBay {category}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  eBay {category} error: {e}")

    print(f"eBay total: {len(products)} products")
    return products
