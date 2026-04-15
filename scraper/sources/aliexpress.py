"""
AliExpress bestsellers scraper.
Tries to extract product data from category pages.
Falls back gracefully if blocked (anti-bot measures are aggressive).
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.aliexpress.com/",
}

# Category pages sorted by most orders
CATEGORIES = [
    ("Electronics", "https://www.aliexpress.com/category/100003109/consumer-electronics.html?SortType=total_tranSqfm_desc"),
    ("Fashion", "https://www.aliexpress.com/category/3/women-s-clothing.html?SortType=total_tranSqfm_desc"),
    ("Home & Garden", "https://www.aliexpress.com/category/13/home-garden.html?SortType=total_tranSqfm_desc"),
    ("Phones", "https://www.aliexpress.com/category/509/mobile-phones.html?SortType=total_tranSqfm_desc"),
    ("Sports", "https://www.aliexpress.com/category/18/sports-entertainment.html?SortType=total_tranSqfm_desc"),
]


def _extract_json_products(html, category, offset=0):
    """Try to extract products from embedded JSON in the page."""
    products = []

    # AliExpress embeds product data in window.runParams
    patterns = [
        r'window\.runParams\s*=\s*({.+?});\s*(?:window|var|\n)',
        r'"items"\s*:\s*(\[.+?\])',
        r'"mods"\s*:\s*({.+?"itemList".+?})',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            continue
        try:
            raw = match.group(1)
            data = json.loads(raw)

            # Navigate to item list
            items = (
                data.get("mods", {}).get("itemList", {}).get("content", [])
                or data.get("items", [])
                or data.get("resultList", [])
            )

            for i, item in enumerate(items[:10]):
                title = (
                    item.get("title", {}).get("displayTitle", "")
                    or item.get("productTitle", "")
                    or item.get("name", "")
                )
                if not title:
                    continue

                price_info = item.get("prices", {}).get("salePrice", {})
                price = f"{price_info.get('currencySymbol', '$')}{price_info.get('minPrice', '')}"
                if price == "$":
                    price = "N/A"

                image = item.get("image", {}).get("imgUrl", "")
                if image and not image.startswith("http"):
                    image = "https:" + image

                product_id = item.get("productId", "") or item.get("itemId", "")
                product_url = (
                    f"https://www.aliexpress.com/item/{product_id}.html"
                    if product_id
                    else ""
                )

                products.append(
                    {
                        "id": f"aliexpress_{category.lower().replace(' ', '_')}_{offset + i}",
                        "name": title[:120],
                        "price": price,
                        "image": image,
                        "url": product_url,
                        "source": "AliExpress",
                        "category": category,
                        "position": offset + i + 1,
                        "rank_change": "",
                        "score": max(10 - i, 1) * 8,
                    }
                )

            if products:
                return products
        except (json.JSONDecodeError, KeyError):
            continue

    return products


def _extract_html_products(html, category, offset=0):
    """Fallback HTML parser for AliExpress."""
    soup = BeautifulSoup(html, "lxml")
    products = []

    selectors = [
        ".list-item",
        "[class*='product-card']",
        "[class*='item-main']",
        ".search-item-card-wrapper-gallery",
    ]
    items = []
    for sel in selectors:
        items = soup.select(sel)
        if items:
            break

    for i, item in enumerate(items[:10]):
        name_el = (
            item.select_one("h1")
            or item.select_one("[class*='title']")
            or item.select_one("a[title]")
        )
        if not name_el:
            continue
        name = name_el.get("title") or name_el.get_text(strip=True)
        if len(name) < 3:
            continue

        price_el = item.select_one("[class*='price']")
        price = price_el.get_text(strip=True) if price_el else "N/A"

        img_el = item.select_one("img")
        image = ""
        if img_el:
            image = img_el.get("src") or img_el.get("data-src") or ""
        if image and not image.startswith("http"):
            image = "https:" + image

        link_el = item.select_one("a[href]")
        product_url = ""
        if link_el:
            href = link_el.get("href", "")
            product_url = "https:" + href if href.startswith("//") else href

        products.append(
            {
                "id": f"aliexpress_{category.lower().replace(' ', '_')}_{offset + i}",
                "name": name[:120],
                "price": price,
                "image": image,
                "url": product_url,
                "source": "AliExpress",
                "category": category,
                "position": offset + i + 1,
                "rank_change": "",
                "score": max(10 - i, 1) * 8,
            }
        )
    return products


def get_trending_products():
    session = requests.Session()
    # Warm up session with a main-page visit for cookies
    try:
        session.get("https://www.aliexpress.com/", headers=HEADERS, timeout=10)
        time.sleep(random.uniform(1, 2))
    except Exception:
        pass

    products = []

    for category, url in CATEGORIES:
        try:
            time.sleep(random.uniform(3, 6))
            response = session.get(url, headers=HEADERS, timeout=20)

            if response.status_code != 200:
                print(f"  AliExpress {category}: HTTP {response.status_code}")
                continue

            # Try JSON extraction first, then HTML fallback
            page_products = _extract_json_products(
                response.text, category, len(products)
            )
            if not page_products:
                page_products = _extract_html_products(
                    response.text, category, len(products)
                )

            products.extend(page_products)
            print(f"  AliExpress {category}: {len(page_products)} items")

        except Exception as e:
            print(f"  AliExpress {category} error: {e}")
            continue

    print(f"AliExpress total: {len(products)} products")
    return products
