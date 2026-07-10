import requests
import json
import sys
import os
from datetime import datetime


class ScraperBase:
    def __init__(self, market_slug, market_name):
        self.market_slug = market_slug
        self.market_name = market_name
        self.offers = []

    def scrape(self):
        raise NotImplementedError

    def add_offer(self, **kwargs):
        if not kwargs.get('product_name'):
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
            print(f"  Trovate {len(self.offers)} offerte")
            self.send_to_api()
            return True
        except Exception as e:
            print(f"  ERRORE: {e}")
            import traceback
            traceback.print_exc()
            return False
