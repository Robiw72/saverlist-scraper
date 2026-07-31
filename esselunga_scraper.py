import re
import requests
from datetime import datetime, timedelta
from base import ScraperBase


VOLANTINI_URL = "https://www.esselunga.it/it-it/promozioni/volantini.html"
GRID_URL = "https://www.esselunga.it/services/istituzionale35/digital-grid.condition:nav_menu.abbrev:ABB.page:0.rows:1000.codPromo:{cod}.json"
STORE_ABBREV = "ABB"

EXCLUDED_FLYER = re.compile(r"casa|persona|raccolta|punti|elettrodomestici|viaggi|occasione", re.I)


class EsselungaScraper(ScraperBase):
    def __init__(self):
        super().__init__("esselunga", "Esselunga")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        }

    def scrape(self):
        flyers = self._get_active_flyers()
        if not flyers:
            print("  Nessun volantino trovato")
            return
        print(f"  Volantini attivi: {[f['name'] for f in flyers]}")

        total = 0
        for flyer in flyers:
            offers = self._fetch_products(flyer["codPromo"])
            for o in offers:
                self.add_offer(**o)
            total += len(offers)
            print(f"    {flyer['name']}: {len(offers)} offerte")

        print(f"  Totale offerte trovate: {total}")

    def _get_active_flyers(self):
        try:
            res = requests.get(VOLANTINI_URL, headers=self.headers, timeout=30)
            if res.status_code != 200:
                return []
        except Exception as e:
            print(f"    Errore lista volantini: {e}")
            return []

        flyers = []
        seen = set()
        for a in re.finditer(r'<a[^>]*flyer-btn[^>]*data-type="scopri"[^>]*>', res.text):
            tag = a.group(0)
            mid = re.search(r'data-id="([^"]+)"', tag)
            mname = re.search(r'data-name="([^"]*)"', tag)
            if not mid:
                continue
            cod = mid.group(1)
            name = (mname.group(1) if mname else cod).strip() or cod
            if cod in seen or EXCLUDED_FLYER.search(name):
                continue
            seen.add(cod)
            flyers.append({"codPromo": cod, "name": name})

        return flyers

    def _fetch_products(self, cod_promo):
        url = GRID_URL.format(cod=cod_promo)
        try:
            res = requests.get(url, headers=self.headers, timeout=60)
            if res.status_code != 200 or "items" not in res.text:
                return []
            data = res.json()
        except Exception as e:
            print(f"    Errore grid {cod_promo}: {e}")
            return []

        offers = []
        for item in data.get("items", []):
            title = (item.get("title") or "").strip()
            if not title:
                continue

            promo = self._first(item.get("promozioni_prezzoPromo"))
            promo_al = self._first(item.get("promozioni_prezzoPromoAl"))
            base = item.get("prezzo") or 0

            price = promo or promo_al
            if not price or price < 0.10 or price > 999:
                continue

            end_date = self._first(item.get("promozioni_dataFinePromoArticolo"))
            end_str = ""
            if end_date:
                end_str = str(end_date)[:10]
            else:
                end_str = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

            offers.append({
                "product_name": title[:200],
                "offer_price": price,
                "original_price": base if base > 0 else None,
                "image_url": item.get("imgUrl") or None,
                "category": "Alimentari",
                "promo_end_date": end_str,
            })

        return offers

    def _first(self, value):
        if isinstance(value, list):
            return value[0] if value else None
        return value
