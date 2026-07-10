import requests
import json
import sys
import os
import re
from datetime import datetime


BLOCKED_NAMES = {
    "supermercati", "supermercato", "ipermercato", "elettronica", "bellezza",
    "giochi per bambini", "giardinaggio e bricolage", "cucina", "copertina",
    "voto:", "contatti", "raccolte punti", "confronta", "buoni sconto",
    "anteprime", "volantini", "catene", "alimentazione", "cura e igiene",
    "materiale elettrico e illuminazione", "igiene e accessori",
    "casa e arredo", "sport e tempo libero", "libri e riviste",
    "animali domestici", "bambini e neonati", "intimo e abbigliamento",
    "scarpe e accessori", "orologi e gioielli", "profumi e cosmetici",
    "integratori e vitamine", "pronto soccorso", "occhiali e lenti",
    "telefonia e accessori", "informatica e tablet", "tv e audio",
    "videogiochi e console", "musica e film", "fai da te",
    "casalinghi e pentole", "tappeti e tende", "letti e materassi",
    "bagno e accessori", "illuminazione", "decorazione",
}

PRICE_PATTERN = re.compile(r'^\s*\d+[.,]\d{2}\s*[€€]?\s*$')
CATEGORY_PATTERN = re.compile(r'^(cibo|igiene|vino|birre|gelati|antipasti|primi|secondi|contorni|pasta|carne|pesce|latte|formaggi|detersivi|shampoo|crema|biscotti|snack|merenda|carta|pane|acqua|bibite|succo|dolci|frutta|verdura|pollo|manzo|maiale|pomodori|insalata|patate|riso|farina|uova|yogurt|burro|mozzarella|parmigiano|prosciutto|salame|tonno|salmone|olio|aceto|sale|zucchero|caffè|tè|cioccolato|marmellata|miele|cereali|muesli|barrette|legumi|zuppe|piatti|surgelati|condimenti|spezie|lieviti|farine|pane|cracker|fette|merendine|caramelle|gelati|budini|torte|crostate|brioche|cornetti|pizza|pane|grissini|taralli|patatine|popcorn|frutta|secca|noci|mandorle|pistacchi|anacardi|arachidi|nocciole|uvetta|albicocche|prugne|datteri|fichi|banane|mele|pere|arance|mandarini|limoni|pompelmi|kiwi|fragole|mirtilli|lamponi|more|ciliegie|pesche|albicocche|susine|meloni|angurie|uve).*', re.IGNORECASE)


class ScraperBase:
    def __init__(self, market_slug, market_name):
        self.market_slug = market_slug
        self.market_name = market_name
        self.offers = []

    def scrape(self):
        raise NotImplementedError

    def is_valid_product_name(self, name):
        if not name or len(name) < 5:
            return False
        name_lower = name.strip().lower()
        if name_lower in BLOCKED_NAMES:
            return False
        if PRICE_PATTERN.match(name):
            return False
        if CATEGORY_PATTERN.match(name_lower):
            return False
        if re.search(r'\b(voto|contatti|raccolte|confronta|buoni|anteprime|volantini|catene)\b', name_lower):
            return False
        return True

    def add_offer(self, **kwargs):
        name = kwargs.get('product_name', '')
        price = kwargs.get('offer_price')
        if not name:
            return
        if not self.is_valid_product_name(name):
            return
        if not price and not kwargs.get('original_price'):
            return
        self.offers.append(kwargs)

    def send_to_api(self):
        if not self.offers:
            print(f"  Nessuna offerta da inviare")
            return

        import config
        url = config.API_URL + "?action=save-offers"
        payload = {"market": self.market_slug, "offers": self.offers}

        try:
            res = requests.post(url, json=payload, timeout=30,
                headers={"User-Agent": "SaverList-Scraper/1.0"})
            data = res.json()
            if data.get("success"):
                print(f"  Inserite: {data['inserted']}, Aggiornate: {data['updated']} su {data['total']}")
            else:
                print(f"  ERRORE API: {data.get('error', 'Sconosciuto')}")
            return data
        except Exception as e:
            print(f"  ERRORE connessione: {e}")
            return None

    def run(self):
        print(f"\n=== {self.market_name} ===")
        try:
            self.scrape()
            print(f"  Trovate {len(self.offers)} offerte valide")
            if self.offers:
                self.send_to_api()
            return True
        except Exception as e:
            print(f"  ERRORE: {e}")
            import traceback
            traceback.print_exc()
            return False
