import requests
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from base import ScraperBase


class ConadScraper(ScraperBase):
    def __init__(self):
        super().__init__("conad", "Conad")

    def scrape(self):
        urls = [
            "https://spesaonline.conad.it/",
            "https://www.volantinoonline.it/conad",
            "https://www.volantinoonline.it/conad/volantini",
        ]

        seen_names = set()

        for url in urls:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                res = requests.get(url, headers=headers, timeout=20)
                res.encoding = "utf-8"

                if res.status_code != 200:
                    continue

                soup = BeautifulSoup(res.text, "lxml")

                # Cerca items
                selectors = [
                    "li", ".product-item", ".offer-item", ".offerta-card",
                    "article", ".product-card", ".item", "[class*=product]",
                    "[class*=offerta]", "[class*=promo]", "tr", ".list-item"
                ]
                items = []
                for sel in selectors:
                    items = soup.select(sel)
                    if len(items) > 2:
                        break

                for item in items:
                    try:
                        text = item.get_text(strip=True)
                        if len(text) < 5:
                            continue

                        name = self._extract_name(item, text)
                        if not name or name in seen_names or len(name) < 3:
                            continue
                        seen_names.add(name)

                        price, original = self._extract_prices(item, text)
                        promo_end = self._extract_date(item, text)
                        discount = self._extract_discount(item, text)
                        category = self._guess_category(name)
                        image = self._extract_image(item)

                        self.add_offer(
                            product_name=name,
                            original_price=original,
                            offer_price=price,
                            discount_value=discount,
                            promo_end_date=promo_end or (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
                            image_url=image,
                            category=category
                        )
                    except:
                        continue

            except Exception as e:
                print(f"  Errore su {url}: {e}")
                continue

    def _extract_name(self, item, text):
        for tag in ["h2", "h3", "h4", "strong", ".title", ".name", ".product-title", "[class*=nome]"]:
            el = item.select_one(tag)
            if el:
                n = el.get_text(strip=True)
                if len(n) > 3:
                    return n
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 4]
        return lines[0][:100] if lines else text[:80].strip()

    def _extract_prices(self, item, text):
        prices = re.findall(r'(\d+[.,]\d{2})\s*[€]', text)
        if not prices:
            prices = re.findall(r'€\s*(\d+[.,]\d{2})', text)
        if prices:
            vals = sorted([float(p.replace(",", ".")) for p in prices])
            if len(vals) >= 2:
                return vals[0], vals[-1]
            return vals[0], None
        return None, None

    def _extract_date(self, item, text):
        patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
            r'scade\s*il\s*(\d{1,2})[/-](\d{1,2})',
            r'fino\s*al\s*(\d{1,2})[/-](\d{1,2})',
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                try:
                    if len(m.groups()) == 3:
                        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                        if y < 100: y += 2000
                        return f"{y:04d}-{mo:02d}-{d:02d}"
                    else:
                        d, mo = int(m.group(1)), int(m.group(2))
                        return f"{datetime.now().year}-{mo:02d}-{d:02d}"
                except:
                    pass
        return None

    def _extract_discount(self, item, text):
        m = re.search(r'(-?\d+%)', text)
        return m.group(1) if m else None

    def _extract_image(self, item):
        img = item.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src", "")
            if src.startswith("//"): src = "https:" + src
            if src.startswith("http"): return src
        return None

    def _guess_category(self, name):
        text = name.lower()
        cats = {
            "Frutta e Verdura": ["mela", "pera", "banana", "arancia", "limone", "insalata", "pomodoro", "zucchina", "carota", "patata", "cipolla", "frutta", "verdura", "uva", "fragola", "lattuga", "broccolo"],
            "Carne e Pesce": ["pollo", "manzo", "maiale", "vitello", "bistecca", "prosciutto", "salame", "pesce", "salmone", "tonno", "carne", "hamburger", "wurstel", "tacchino", "orata", "branzino"],
            "Latte e Formaggi": ["latte", "formaggio", "yogurt", "burro", "mozzarella", "parmigiano", "ricotta", "stracchino", "gorgonzola", "grana", "provolone"],
            "Pasta e Riso": ["pasta", "spaghetti", "penne", "riso", "farina", "pane", "cracker", "fette biscottate", "cous", "grano"],
            "Bevande": ["acqua", "bibita", "succo", "vino", "birra", "caffè", "caffe", "tè", "te", "cioccolata", "coca", "fanta", "sprite", "analcolico", "prosecco", "spumante"],
            "Detersivi e Pulizia": ["detersivo", "ammorbidente", "candeggina", "pulizia", "lavastoviglie", "lavatrice", "sgrassatore", "casa", "igienizzante"],
            "Cura Persona": ["shampoo", "crema", "dentifricio", "deodorante", "sapone", "bagnoschiuma", "profumo"],
            "Dolci e Snack": ["biscotto", "cioccolato", "snack", "merendina", "torta", "dolce", "gelato", "caramella", "patatina", "nutella", "budino", "merenda"],
            "Casa": ["carta", "tovagliolo", "scottex", "alluminio", "pellicola", "sacchetto", "carta igienica"],
        }
        for cat, keywords in cats.items():
            if any(k in text for k in keywords):
                return cat
        return "Alimentari"


if __name__ == "__main__":
    s = ConadScraper()
    s.run()
