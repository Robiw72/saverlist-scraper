#!/usr/bin/env python3
"""
Esegue tutti gli scraper e invia i dati all'app su InfinityFree.
Uso: python run_all.py
"""
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cleanup():
    import config
    try:
        res = requests.get(config.API_URL + "?action=cleanup", timeout=15,
            headers={"User-Agent": "SaverList-Scraper/1.0"})
        data = res.json()
        if data.get("success"):
            print(f"  Pulizia: {data.get('message', 'OK')}")
    except Exception as e:
        print(f"  ERRORE cleanup: {e}")


def main():
    print("=" * 50)
    print("  SaverList Market - Scraper")
    print("=" * 50)

    from gigante import GiganteScraper
    from conad import ConadScraper
    from esselunga import EsselungaScraper

    scrapers = [ConadScraper(), GiganteScraper(), EsselungaScraper()]

    for s in scrapers:
        s.run()

    print("\n=== Pulizia offerte scadute ===")
    cleanup()

    print("\n=== Completato! ===")


if __name__ == "__main__":
    main()
