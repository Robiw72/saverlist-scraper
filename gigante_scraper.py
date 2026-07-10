import re
from datetime import datetime, timedelta
from base import ScraperBase

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


CATEGORY_URLS = [
    "https://www.ilgigante.it/it/offerte/",
]


class GiganteScraper(ScraperBase):
    def __init__(self):
        super().__init__("gigante", "Il Gigante")

    def scrape(self):
        if not HAS_PLAYWRIGHT:
            print(f"  Playwright non installato")
            return

        offers = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(30000)

                for url in CATEGORY_URLS:
                    try:
                        page.goto(url, wait_until="networkidle")
                        items = self._extract_offers(page)
                        offers.extend(items)
                    except Exception as e:
                        print(f"    Errore {url}: {e}")
                        continue

                browser.close()
        except Exception as e:
            print(f"  ERRORE: {e}")
            return

        for o in offers:
            self.add_offer(**o)
        print(f"  Totale offerte trovate: {len(offers)}")

    def _extract_offers(self, page):
        offers = []

        product_cards = page.query_selector_all(
            '[class*="product"], [class*="offer"], [class*="promo"], [class*="card"]'
        )

        for card in product_cards:
            try:
                text = card.inner_text()
                html = card.inner_html()
            except Exception:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if len(lines) < 2:
                continue

            name = lines[0]
            price = None
            for line in lines:
                m = re.search(r"(\d+[.,]\d{2})\s*[€€]", line)
                if not m:
                    m = re.search(r"[€€]\s*(\d+[.,]\d{2})", line)
                if m:
                    try:
                        price = float(m.group(1).replace(",", "."))
                    except ValueError:
                        continue
                    if "al kg" in line.lower() or "/kg" in line.lower():
                        continue
                    break

            if not price or price > 999 or price < 0.10:
                continue

            offers.append({
                "product_name": name[:200],
                "offer_price": price,
                "promo_end_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
                "category": "Alimentari",
            })

        return offers
