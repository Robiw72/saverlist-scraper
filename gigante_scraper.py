import re
import json
import requests
from datetime import datetime
from base import ScraperBase


VENDOR_URL = "https://ilvolantino.it/negozio/il-gigante"
COMPANY_CODE = "IL_GIGANTE"
IMAGE_CDN = "https://cdn.ilvolantino.it/images/{name}"


class GiganteScraper(ScraperBase):
    def __init__(self):
        super().__init__("gigante", "Il Gigante")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        }

    def scrape(self):
        try:
            res = requests.get(VENDOR_URL, headers=self.headers, timeout=30)
            if res.status_code != 200:
                print(f"  Errore HTTP {res.status_code}")
                return
        except Exception as e:
            print(f"  Errore connessione: {e}")
            return

        products = self._parse_products(res.text)
        today = datetime.now().strftime("%Y-%m-%d")

        for p in products:
            if p.get("companyCode") != COMPANY_CODE:
                continue
            if p.get("validTo", "9999-12-31") < today:
                continue
            self.add_offer(**self._to_offer(p))

        print(f"  Totale offerte trovate: {len(self.offers)}")

    def _parse_products(self, html):
        chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)</script>', html, re.S)
        full = ""
        for c in chunks:
            try:
                full += json.loads('"' + c + '"')
            except Exception:
                continue

        products = []
        for m in re.finditer(r'\{"id":\d+,"name":"', full):
            start = m.start()
            depth = 0
            i = start
            while i < len(full):
                if full[i] == "{":
                    depth += 1
                elif full[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            if depth != 0:
                continue
            try:
                obj = json.loads(full[start:i + 1])
            except Exception:
                continue
            if "price" in obj and "urlPath" in obj:
                products.append(obj)

        return products

    def _to_offer(self, p):
        name = (p.get("name") or "").strip()
        quantity = (p.get("quantity") or "").strip()
        if quantity:
            name = f"{name} {quantity}"

        original = p.get("regularPrice") or 0
        offer_price = p.get("price") or 0

        return {
            "product_name": name[:200],
            "description": (p.get("description") or "").strip() or None,
            "offer_price": offer_price,
            "original_price": original if original > 0 else None,
            "discount_type": "percent",
            "discount_value": p.get("discount") or None,
            "promo_end_date": p.get("validTo"),
            "image_url": IMAGE_CDN.format(name=p.get("image")) if p.get("image") else None,
            "category": (p.get("topCategoryName") or p.get("categoryName") or "Alimentari"),
        }
