"""
AliExpress bestsellers scraper using Playwright.
Renders the page with a real browser so JavaScript-heavy content loads properly.
"""
import json
import re
import time
import random

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CATEGORIES = [
    ("Electronics",  "https://www.aliexpress.com/category/100003109/consumer-electronics.html?SortType=total_tranSqfm_desc"),
    ("Fashion",      "https://www.aliexpress.com/category/3/women-s-clothing.html?SortType=total_tranSqfm_desc"),
    ("Home & Garden","https://www.aliexpress.com/category/13/home-garden.html?SortType=total_tranSqfm_desc"),
    ("Phones",       "https://www.aliexpress.com/category/509/mobile-phones.html?SortType=total_tranSqfm_desc"),
    ("Sports",       "https://www.aliexpress.com/category/18/sports-entertainment.html?SortType=total_tranSqfm_desc"),
    ("Beauty",       "https://www.aliexpress.com/category/66/hair-extensions-wigs.html?SortType=total_tranSqfm_desc"),
    ("Toys",         "https://www.aliexpress.com/category/1501/toys-hobbies.html?SortType=total_tranSqfm_desc"),
]


def _extract_from_json(content, category, offset):
    """Try to pull products from window.runParams JSON embedded in the page."""
    products = []
    match = re.search(
        r'window\.runParams\s*=\s*(\{.+?\});\s*(?:window|var|\n)',
        content, re.DOTALL
    )
    if not match:
        return products
    try:
        data = json.loads(match.group(1))
        items = data.get("mods", {}).get("itemList", {}).get("content", [])
        for i, item in enumerate(items[:12]):
            title = item.get("title", {}).get("displayTitle", "")
            if not title:
                continue
            price_info = item.get("prices", {}).get("salePrice", {})
            price = f"{price_info.get('currencySymbol','$')}{price_info.get('minPrice','')}"
            if price.strip() in ("$", ""):
                price = "N/A"
            image = item.get("image", {}).get("imgUrl", "")
            if image and not image.startswith("http"):
                image = "https:" + image
            pid = item.get("productId", "")
            url = f"https://www.aliexpress.com/item/{pid}.html" if pid else ""
            products.append({
                "id": f"aliexpress_{category.lower().replace(' ','_')}_{offset+i}",
                "name": title[:120],
                "price": price,
                "image": image,
                "url": url,
                "source": "AliExpress",
                "category": category,
                "position": offset + i + 1,
                "rank_change": "",
                "score": max(12 - i, 1) * 8,
            })
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return products


def _extract_from_dom(page, category, offset):
    """Fallback: query rendered DOM for product cards."""
    products = []
    card_selectors = [
        "[class*='product-container']",
        "[class*='item-card']",
        "[class*='list-item']",
        "[class*='search-item-card']",
        "a[href*='/item/']",
    ]
    cards = []
    for sel in card_selectors:
        cards = page.query_selector_all(sel)
        if len(cards) >= 3:
            break

    for i, card in enumerate(cards[:12]):
        try:
            title_el = (
                card.query_selector("[class*='title']")
                or card.query_selector("h1,h2,h3")
            )
            title = (title_el.inner_text().strip() if title_el else
                     card.get_attribute("title") or "")
            if len(title) < 4:
                continue

            price_el = card.query_selector("[class*='price']")
            price = price_el.inner_text().strip() if price_el else "N/A"

            img_el = card.query_selector("img")
            image = ""
            if img_el:
                image = (img_el.get_attribute("src") or
                         img_el.get_attribute("data-src") or "")
            if image and not image.startswith("http"):
                image = "https:" + image

            link_el = card.query_selector("a[href]") or card
            href = link_el.get_attribute("href") or ""
            if href.startswith("//"):
                href = "https:" + href

            products.append({
                "id": f"aliexpress_{category.lower().replace(' ','_')}_dom_{offset+i}",
                "name": title[:120],
                "price": price,
                "image": image,
                "url": href,
                "source": "AliExpress",
                "category": category,
                "position": offset + i + 1,
                "rank_change": "",
                "score": max(12 - i, 1) * 8,
            })
        except Exception:
            continue
    return products


def get_trending_products():
    products = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = ctx.new_page()

        # Visit homepage to pick up cookies / bypass redirects
        try:
            page.goto("https://www.aliexpress.com/", timeout=25000,
                      wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
        except Exception:
            pass

        for category, url in CATEGORIES:
            try:
                time.sleep(random.uniform(2, 4))
                page.goto(url, timeout=35000, wait_until="domcontentloaded")

                # Wait for product grid to appear
                try:
                    page.wait_for_selector(
                        "[class*='product-container'],[class*='item-card'],[class*='list-item']",
                        timeout=10000,
                    )
                except PWTimeout:
                    pass  # Try anyway

                page.wait_for_timeout(2000)
                content = page.content()

                # Try JSON extraction first
                page_products = _extract_from_json(content, category, len(products))

                # Fallback to DOM scraping
                if not page_products:
                    page_products = _extract_from_dom(page, category, len(products))

                products.extend(page_products)
                print(f"  AliExpress {category}: {len(page_products)} items")

            except Exception as e:
                print(f"  AliExpress {category} error: {e}")

        browser.close()

    print(f"AliExpress total: {len(products)} products")
    return products
