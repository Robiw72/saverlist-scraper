import os
import re
import html as html_mod
import json
import time
import requests
import config
from datetime import datetime, timedelta
from base import ScraperBase


CONAD_BASE = "https://spesaonline.conad.it"

MAIN_CATEGORIES = [
    "/c/frutta-e-verdura--01",
    "/c/carne-e-salumi--02",
    "/c/prodotti-ittici--03",
    "/c/latte-latticini-e-uova--04",
    "/c/preparati-torte-e-pizze--05",
    "/c/dolci-per-colazione-e-merenda--06",
    "/c/bevande-calde--07",
    "/c/conserve-salse-condimenti--08",
    "/c/prodotti-da-forno--09",
    "/c/pasta-e-riso--10",
    "/c/surgelati-e-gelati--11",
    "/c/piatti-pronti--12",
    "/c/bevande-e-bibite-analcoliche--18",
]

CARD_RE = re.compile(
    r'data-product="([^"]{10,})".*?'
    r'product-price-red product-price[^>]*>\s*([\d.,]+)\s*[€€]?',
    re.DOTALL,
)


class ConadScraper(ScraperBase):
    def __init__(self):
        super().__init__("conad", "Conad")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"
        }

    def scrape(self):
        total = 0
        for i, cat in enumerate(MAIN_CATEGORIES):
            if i > 0:
                time.sleep(1.5)
            offers = self._scrape_category(cat)
            for o in offers:
                self.add_offer(**o)
            total += len(offers)
            print(f"    {cat}: {len(offers)} offerte")

        print(f"  Totale offerte trovate: {total}")

    def _scrape_category(self, cat_path):
        offers = []
        url = CONAD_BASE + cat_path
        res = None
        for attempt in range(2):
            try:
                res = requests.get(url, headers=self.headers, timeout=30)
                res.encoding = 'utf-8'
                if res.status_code == 200 and 'data-product' in res.text:
                    break
            except Exception:
                pass
            if attempt == 0:
                time.sleep(5)
        if res is None or res.status_code != 200 or 'data-product' not in res.text:
            return []

        for m in CARD_RE.finditer(res.text):
            try:
                data = json.loads(html_mod.unescape(m.group(1)))
            except (json.JSONDecodeError, ValueError):
                continue

            name = (data.get("nome") or "").strip()
            if not name:
                continue

            price = self._parse_price(m.group(2))
            if not price or price < 0.10 or price > 999:
                continue

            offers.append({
                "product_name": name[:200],
                "offer_price": price,
                "image_url": data.get("defaultImgSrc") or None,
                "category": data.get("categoriaPrimoLivello") or "Alimentari",
                "promo_end_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            })

        return offers

    def _parse_price(self, s):
        s = s.strip().replace("\u20ac", "").replace(" ", "")
        m = re.match(r"^(\d+[.,]\d{1,2})$", s)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
