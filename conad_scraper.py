import os
import requests
import config
from datetime import datetime, timedelta
from base import ScraperBase


PARSE_BASE = "https://api.parse.bot/scraper/06ee45ae-1dba-4ce9-ae30-5a07b6011c0e"

SUB_CATEGORY_DEPTH = {}


class ConadScraper(ScraperBase):
    def __init__(self):
        super().__init__("conad", "Conad")

    def scrape(self):
        api_key = os.environ.get("PARSE_BOT_API_KEY") or config.PARSE_BOT_API_KEY
        if not api_key:
            print(f"  PARSE_BOT_API_KEY non configurata in config.py")
            return

        self.headers = {"X-API-Key": api_key, "User-Agent": "SaverList-Scraper/1.0"}

        categories = self._get_categories()
        if not categories:
            print(f"  Nessuna categoria trovata")
            return

        main_cats = [c for c in categories if self._is_main_category(c)][:8]

        total = 0
        for cat in main_cats:
            offers = self._scrape_category(cat)
            for o in offers:
                self.add_offer(**o)
            total += len(offers)

        print(f"  Totale offerte trovate: {total}")

    def _get_categories(self):
        try:
            res = requests.get(f"{PARSE_BASE}/get_categories", headers=self.headers, timeout=20)
            data = res.json()
            d = data.get("data") or {}
            return d.get("categories") or []
        except Exception as e:
            print(f"  Errore categorie: {e}")
            return []

    def _is_main_category(self, cat):
        slug = cat.get("slug", "")
        if not slug:
            return False
        depth = slug.count("-")
        return depth <= 3

    def _scrape_category(self, cat):
        slug = cat.get("slug", "")
        if not slug:
            return []

        offers = []
        try:
            for page in range(2):
                res = requests.get(
                    f"{PARSE_BASE}/get_products_by_category",
                    params={"category_slug": slug, "page": page},
                    headers=self.headers, timeout=20
                )
                if res.status_code != 200:
                    break
                data = res.json()
                d = data.get("data") or data
                products = d.get("products") or []
                if not products:
                    break

                for p in products:
                    name = (p.get("name") or "").strip()
                    price = p.get("base_price") or 0
                    try:
                        price = float(price)
                    except (ValueError, TypeError):
                        continue
                    if price <= 0:
                        continue
                    offers.append({
                        "product_name": name[:200],
                        "offer_price": price,
                        "promo_end_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
                        "category": "Alimentari",
                    })
        except Exception as e:
            print(f"    Errore categoria {slug}: {e}")

        return offers
