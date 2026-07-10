import requests
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from base import ScraperBase


class GiganteScraper(ScraperBase):
    def __init__(self):
        super().__init__("gigante", "Il Gigante")

    def scrape(self):
        urls = [
            "https://www.volantinoonline.it/il-gigante",
            "https://www.volantinoonline.it/il-gigante/volantini",
            "https://www.centrovolantini.it/volantino-il-gigante",
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

                selectors = [
                    ".offer-item", ".product-item", ".offerta-card",
                    ".product-card", "[class*=offerta]", "[class*=product]",
                    "[class*=promo]", "article", ".list-item",
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
                        if not name or name in seen_names or len(name) < 4:
                            continue
                        seen_names.add(name)

                        price, original = self._extract_prices(item, text)
                        promo_end = self._extract_date(item, text)
                        discount = self._extract_discount(item, text)
                        category = self._guess_category(name)
                        image = self._extract_image(item)

                        if not price and not original:
                            continue

                        self.add_offer(
                            product_name=name,
                            description=None,
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
        for tag in ["h2", "h3", "h4", "strong", "a.title", ".title", ".name"]:
            el = item.select_one(tag)
            if el:
                name = el.get_text(strip=True)
                if len(name) > 3:
                    return name
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 4 and not re.match(r'^[\d.,\s€%\-]+$', l.strip())]
        return lines[0][:100] if lines else None

    def _extract_prices(self, item, text):
        prices = re.findall(r'(\d+[.,]\d{2})\s*[€]', text)
        if prices:
            vals = sorted([float(p.replace(",", ".")) for p in prices])
            if len(vals) >= 2:
                return vals[0], vals[-1]
            return vals[0], None
        return None, None

    def _extract_date(self, item, text):
        patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
            r'fino\s*al\s*(\d{1,2})\s*[/-]\s*(\d{1,2})',
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
        m = re.search(r'(-?\d+%|-?\d+%)', text)
        return m.group(1) if m else None

    def _extract_image(self, item):
        img = item.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src", "")
            if src.startswith("//"):
                src = "https:" + src
            if src.startswith("http"):
                return src
        return None

    def _guess_category(self, name):
        text = name.lower()
        cats = {
            "Frutta e Verdura": ["mela", "pera", "banana", "arancia", "limone", "insalata", "pomodoro", "zucchina", "carota", "patata", "cipolla", "frutta", "verdura", "uva", "fragola"],
            "Carne e Pesce": ["pollo", "manzo", "maiale", "vitello", "bistecca", "prosciutto", "salame", "pesce", "salmone", "tonno", "carne", "hamburger", "wurstel"],
            "Latte e Formaggi": ["latte", "formaggio", "yogurt", "burro", "mozzarella", "parmigiano", "ricotta", "stracchino", "gorgonzola"],
            "Pasta e Riso": ["pasta", "spaghetti", "penne", "riso", "farina", "pane", "cracker", "fette"],
            "Bevande": ["acqua", "bibita", "succo", "vino", "birra", "caffè", "caffe", "tè", "te", "cioccolata", "coca", "fanta", "sprite"],
            "Detersivi e Pulizia": ["detersivo", "ammorbidente", "candeggina", "pulizia", "lavastoviglie", "lavatrice", "sgrassatore"],
            "Cura Persona": ["shampoo", "crema", "dentifricio", "deodorante", "sapone", "bagnoschiuma"],
            "Dolci e Snack": ["biscotto", "cioccolato", "snack", "merendina", "torta", "dolce", "gelato", "caramella", "patatina", "nutella"],
            "Casa": ["carta", "tovagliolo", "scottex", "alluminio", "pellicola", "sacchetto"],
        }
        for cat, keywords in cats.items():
            if any(k in text for k in keywords):
                return cat
        return "Alimentari"


if __name__ == "__main__":
    s = GiganteScraper()
    s.run()
