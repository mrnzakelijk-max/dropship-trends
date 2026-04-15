"""
Main aggregator for the Dropship Trending Products scraper.

Runs all source scrapers, deduplicates and scores results,
then writes docs/data.json for the GitHub Pages dashboard.
"""
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

# Make sure local imports work when run from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sources.amazon import get_trending_products as get_amazon
from sources.ebay import get_trending_products as get_ebay
from sources.aliexpress import get_trending_products as get_aliexpress
from sources.google_trends import get_trending_searches as get_google
from sources.reddit import get_trending_products as get_reddit


def normalize(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", name.lower())).strip()


def name_similarity(a: str, b: str) -> float:
    """Return similarity ratio between two product names."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def merge_products(raw: list) -> list:
    """
    Deduplicate products from different sources.
    Products with >75% name similarity are merged; their scores are summed
    and all source names are collected.
    """
    merged = []  # list of dicts

    for product in raw:
        best_match_idx = None
        best_ratio = 0.0

        for idx, existing in enumerate(merged):
            ratio = name_similarity(product["name"], existing["name"])
            if ratio > best_ratio:
                best_ratio = ratio
                best_match_idx = idx

        if best_ratio >= 0.75 and best_match_idx is not None:
            existing = merged[best_match_idx]
            # Accumulate sources
            if product["source"] not in existing["sources"]:
                existing["sources"].append(product["source"])
            # Boost score for cross-platform appearance
            existing["score"] += product["score"]
            # Prefer real prices and images over placeholders
            if existing["price"] == "N/A" and product["price"] != "N/A":
                existing["price"] = product["price"]
            if not existing.get("image") and product.get("image"):
                existing["image"] = product["image"]
        else:
            entry = dict(product)
            entry["sources"] = [product["source"]]
            merged.append(entry)

    # Sort by score descending
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged


def run():
    print(f"=== Dropship Trends Scraper — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} ===\n")

    scrapers = [
        ("amazon", get_amazon),
        ("ebay", get_ebay),
        ("aliexpress", get_aliexpress),
        ("google_trends", get_google),
        ("reddit", get_reddit),
    ]

    all_products = []
    source_stats = {}

    for source_name, fn in scrapers:
        print(f"\n[{source_name.upper()}]")
        try:
            products = fn()
            all_products.extend(products)
            source_stats[source_name] = {"status": "success", "count": len(products)}
        except Exception as e:
            print(f"  FAILED: {e}")
            source_stats[source_name] = {"status": "error", "count": 0, "error": str(e)}

    print(f"\n--- Raw total: {len(all_products)} products across all sources ---")

    merged = merge_products(all_products)
    print(f"--- After deduplication: {len(merged)} unique products ---")

    # Assign final rank
    for i, p in enumerate(merged):
        p["rank"] = i + 1

    output = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_products": len(merged),
        "sources": source_stats,
        "products": merged[:300],  # publish top 300
    }

    out_path = Path(__file__).parent.parent / "docs" / "data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(merged)} products → {out_path}")
    print("Done.")


if __name__ == "__main__":
    run()
