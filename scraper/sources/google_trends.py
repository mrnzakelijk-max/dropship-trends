"""
Google Trends scraper via pytrends.
Gets trending shopping-related search terms globally.
"""
from pytrends.request import TrendReq
import time

# Keywords that indicate a trending topic is news/entertainment, not a product
NEWS_FILTERS = [
    "died", "death", "killed", "shooting", "earthquake", "hurricane",
    "election", "president", "war", "attack", "arrested", "trial",
    "vs", "game", "score", "match", "finale", "season",
]

# Countries to pull trending searches from
COUNTRIES = ["united_states", "united_kingdom", "australia", "canada", "germany"]


def _is_likely_product(term):
    """Basic heuristic: exclude obvious news/sports/celebrity terms."""
    t = term.lower()
    return not any(kw in t for kw in NEWS_FILTERS)


def get_trending_searches():
    pytrends = TrendReq(
        hl="en-US",
        tz=360,
        timeout=(10, 30),
        retries=2,
        backoff_factor=0.5,
    )

    seen = set()
    candidates = []

    for country in COUNTRIES:
        try:
            time.sleep(2)
            df = pytrends.trending_searches(pn=country)
            for term in df[0].tolist()[:30]:
                if term not in seen and _is_likely_product(term):
                    seen.add(term)
                    candidates.append(term)
        except Exception as e:
            print(f"  Google Trends {country} error: {e}")

    if not candidates:
        print("Google Trends: no candidates found")
        return []

    # Score the top candidates using interest_over_time
    products = []
    batch = candidates[:25]  # pytrends limit is 5 per request

    for i in range(0, min(len(batch), 25), 5):
        chunk = batch[i : i + 5]
        try:
            time.sleep(3)
            pytrends.build_payload(chunk, timeframe="today 1-m", geo="")
            interest = pytrends.interest_over_time()

            for j, term in enumerate(chunk):
                score = 50
                if not interest.empty and term in interest.columns:
                    score = int(interest[term].mean())

                products.append(
                    {
                        "id": f"gtrends_{i + j}",
                        "name": term,
                        "price": "N/A",
                        "image": "",
                        "url": f"https://www.google.com/search?q={term.replace(' ', '+')}+buy",
                        "source": "Google Trends",
                        "category": "Trending Search",
                        "position": i + j + 1,
                        "rank_change": "",
                        "score": score,
                    }
                )
        except Exception as e:
            print(f"  Google Trends interest batch error: {e}")
            # Add with default scores if interest lookup fails
            for j, term in enumerate(chunk):
                if not any(p["name"] == term for p in products):
                    products.append(
                        {
                            "id": f"gtrends_{i + j}",
                            "name": term,
                            "price": "N/A",
                            "image": "",
                            "url": f"https://www.google.com/search?q={term.replace(' ', '+')}+buy",
                            "source": "Google Trends",
                            "category": "Trending Search",
                            "position": i + j + 1,
                            "rank_change": "",
                            "score": max(25 - (i + j), 5),
                        }
                    )

    print(f"Google Trends total: {len(products)} products")
    return products
