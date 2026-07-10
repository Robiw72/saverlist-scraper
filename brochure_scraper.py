import requests
import re
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from io import BytesIO

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

from base import ScraperBase


BROCHURE_SOURCES = {
    "conad": {"name": "Conad", "list_url": "https://www.volantinoonline.it/conad/volantini", "slug": "conad", "url_key": "conad"},
    "gigante": {"name": "Il Gigante", "list_url": "https://www.volantinoonline.it/il-gigante/volantini", "slug": "gigante", "url_key": "il-gigante"},
    "esselunga": {"name": "Esselunga", "list_url": "https://www.volantinoonline.it/esselunga/volantini", "slug": "esselunga", "url_key": "esselunga"},
}


class BrochureScraper(ScraperBase):
    def __init__(self, market_slug):
        info = BROCHURE_SOURCES[market_slug]
        super().__init__(market_slug, info["name"])
        self.list_url = info["list_url"]
        self.base_url = "https://www.volantinoonline.it"

    def scrape(self):
        if not HAS_OCR:
            print(f"  OCR non disponibile (pytesseract non installato)")
            return

        import subprocess, os
        import pytesseract as pt
        tesseract_cmd = "tesseract"
        if os.name == "nt":
            for path in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
                if os.path.exists(path):
                    tesseract_cmd = path
                    pt.pytesseract.tesseract_cmd = path
                    break
        if not os.environ.get("TESSDATA_PREFIX"):
            for d in [r"C:\Program Files\Tesseract-OCR\tessdata", os.path.expanduser("~/tessdata")]:
                if os.path.isdir(d):
                    os.environ["TESSDATA_PREFIX"] = d
                    break
        try:
            subprocess.run([tesseract_cmd, "--version"], capture_output=True, check=True)
        except:
            print(f"  Tesseract non trovato nel PATH")
            return

        brochures = self._get_active_brochures()
        if not brochures:
            print(f"  Nessun volantino trovato")
            return

        print(f"  {len(brochures)} volantini disponibili, elaboro il più recente")

        bro = brochures[0]
        pages = self._get_brochure_pages(bro["detail_url"])
        if not pages:
            print(f"  Nessuna pagina trovata")
            return

        max_pages = min(len(pages), 15)
        print(f"  Volantino: {len(pages)} pagine (elaboro prime {max_pages})")

        total_offers = 0
        for page_url in pages[:max_pages]:
            try:
                offers = self._ocr_page(page_url, bro)
                for off in offers:
                    self.add_offer(**off)
                total_offers += len(offers)
            except Exception as e:
                print(f"    ERRORE: {e}")
                continue

        print(f"  Totale offerte trovate: {total_offers}")

    def _get_active_brochures(self):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            res = requests.get(self.list_url, headers=headers, timeout=20)
            if res.status_code != 200:
                return []
            soup = BeautifulSoup(res.text, "lxml")
            brochures = []
            seen_ids = set()
            url_key = BROCHURE_SOURCES[self.market_slug]["url_key"]
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if f"/{url_key}/volantino/" in href:
                    bro_id = href.split("/")[-1]
                    if bro_id in seen_ids:
                        continue
                    seen_ids.add(bro_id)
                    detail_url = href if href.startswith("http") else self.base_url + href
                    txt = a.get_text(strip=True)
                    date_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", txt)
                    end_date = None
                    if date_match:
                        d, mo, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                        if y < 100: y += 2000
                        end_date = f"{y:04d}-{mo:02d}-{d:02d}"
                    brochures.append({"id": bro_id, "detail_url": detail_url, "end_date": end_date})
            brochures.sort(key=lambda b: b.get("end_date", ""), reverse=True)
            return brochures
        except Exception as e:
            print(f"  Errore lista: {e}")
            return []

    def _get_brochure_pages(self, detail_url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            res = requests.get(detail_url, headers=headers, timeout=20)
            if res.status_code != 200:
                return []
            match = re.search(r'images:\s*(\[.*?\])', res.text, re.DOTALL)
            if not match:
                return []
            images = json.loads(match.group(1))
            full_urls = []
            for img in images:
                if img.startswith("//"): full_urls.append("https:" + img)
                elif img.startswith("/"): full_urls.append(self.base_url + img)
                elif not img.startswith("http"): full_urls.append(self.base_url + "/" + img)
                else: full_urls.append(img)
            return full_urls
        except Exception as e:
            print(f"  Errore pagine: {e}")
            return []

    def _preprocess_image(self, img):
        img = img.convert("RGB")
        w, h = img.size
        img = img.resize((w * 2, h * 2), Image.LANCZOS)
        gray = img.convert("L")
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = ImageOps.autocontrast(gray, cutoff=5)
        gray = gray.point(lambda x: 0 if x < 140 else 255)
        return gray

    def _ocr_page(self, image_url, brochure_info):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            resp = requests.get(image_url, headers=headers, timeout=30, stream=True)
            if resp.status_code != 200:
                return []
            img = Image.open(BytesIO(resp.content))

            processed = self._preprocess_image(img)
            custom_config = r"--oem 3 --psm 6 -l ita"
            text = pytesseract.image_to_string(processed, config=custom_config)

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                print(f"    OCR {image_url.split('/')[-1]}: {len(lines)} righe trovate")
                debug = [ln for ln in lines if len(ln) > 5][:5]
                if debug:
                    print(f"    DEBUG OCR sample: {' | '.join(debug)}")

            return self._parse_ocr_text(text, brochure_info)
        except Exception as e:
            print(f"    ERRORE OCR {image_url.split('/')[-1]}: {e}")
            return []

    def _clean_name(self, name):
        name = re.sub(r"[^a-zA-Zàèéìòù0-9.,€%%\s/'#-]", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        trash = r"\b(credito|sponsor|prodotto|acquistando|ottieni|giocate|extra|possibilità|concorso|aumenta|buona|spesa|qualità|disponibili|filiali)\b"
        name = re.sub(trash, "", name, flags=re.IGNORECASE)
        name = re.sub(r"\s+", " ", name).strip()
        if len(name) < 4:
            return None
        return name[:200]

    def _parse_ocr_text(self, text, brochure_info):
        offers = []
        lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 2]

        price_pattern = re.compile(r"(?:€)?\s*(\d+[.,]\d{2})\s*(?:€)?")
        current_name = []

        for line in lines:
            cleaned = re.sub(r"[^a-zA-Zàèéìòù0-9.,€%%\s/'#-]", " ", line).strip()
            if not cleaned:
                continue

            has_price = False
            for m in price_pattern.finditer(cleaned):
                price_str = m.group(1).replace(",", ".")
                try:
                    price = float(price_str)
                except ValueError:
                    continue
                if not (0.10 < price < 999):
                    continue
                name_before = cleaned[:m.start()].strip()
                if name_before:
                    name = self._clean_name(name_before)
                    if name:
                        offers.append({
                            "product_name": name,
                            "offer_price": price,
                            "promo_end_date": brochure_info.get("end_date") or (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
                            "category": "Alimentari",
                        })
                elif current_name:
                    full = " ".join(current_name)
                    name = self._clean_name(full)
                    if name:
                        offers.append({
                            "product_name": name,
                            "offer_price": price,
                            "promo_end_date": brochure_info.get("end_date") or (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
                            "category": "Alimentari",
                        })
                has_price = True
                break

            if has_price:
                current_name = []
            else:
                if not re.match(r"^[\d.,\s€%\-\/]+$", cleaned):
                    current_name.append(cleaned)
                    if len(current_name) > 3:
                        current_name.pop(0)

        end_date = brochure_info.get("end_date") or (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        offers = [o for o in offers if o["offer_price"] >= 0.30]
        
        seen = set()
        deduped = []
        for o in offers:
            key = (o["product_name"].lower(), o["offer_price"])
            if key not in seen:
                seen.add(key)
                deduped.append(o)
        return deduped


if __name__ == "__main__":
    import sys
    for m in ["conad", "gigante", "esselunga"]:
        s = BrochureScraper(m)
        s.run()
        print(f"  Totale offerte: {len(s.offers)}")
