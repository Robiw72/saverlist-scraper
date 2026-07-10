import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from base import ScraperBase

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class EsselungaScraper(ScraperBase):
    def __init__(self):
        super().__init__("esselunga", "Esselunga")

    def scrape(self):
        offers = []

        if HAS_PLAYWRIGHT:
            pw_offers = self._scrape_playwright()
            offers.extend(pw_offers)

        for o in offers:
            self.add_offer(**o)
        print(f"  Totale offerte trovate: {len(offers)}")

    def _scrape_playwright(self):
        offers = []
        urls = [
            "https://www.esselunga.it/promozioni",
        ]

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(30000)

                for url in urls:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(3000)
                        content = page.content()
                        soup = BeautifulSoup(content, "lxml")
                        items = self._parse_html(soup)
                        offers.extend(items)
                    except Exception as e:
                        print(f"    Errore {url}: {e}")
                        continue

                browser.close()
        except Exception as e:
            print(f"  ERRORE Playwright: {e}")

        return offers

    def _parse_html(self, soup):
        offers = []
        text_blocks = soup.find_all(["div", "article", "section"],
                                    class_=re.compile(r"(product|offer|promo|card|item)", re.I))

        if not text_blocks:
            text_blocks = soup.find_all(["div", "li", "article"],
                                        attrs={"data-product": True})

        if not text_blocks:
            text_blocks = soup.find_all("div", class_=True)

        seen = set()
        for block in text_blocks:
            text = block.get_text(strip=True)
            if not text or len(text) < 10:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            name = lines[0] if lines else text[:100]
            if len(name) < 5:
                continue

            price = None
            for line in lines:
                m = re.search(r"[€€]\s*(\d+[.,]\d{2})", line)
                if not m:
                    m = re.search(r"(\d+[.,]\d{2})\s*[€€]", line)
                if m:
                    try:
                        p = float(m.group(1).replace(",", "."))
                        if 0.10 < p < 999:
                            price = p
                            break
                    except ValueError:
                        continue

            if not price:
                continue

            key = (name[:50].lower(), price)
            if key in seen:
                continue
            seen.add(key)

            offers.append({
                "product_name": name[:200],
                "offer_price": price,
                "promo_end_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
                "category": "Alimentari",
            })

        return offers
