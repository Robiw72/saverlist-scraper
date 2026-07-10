#!/usr/bin/env python3
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

    from brochure_scraper import BrochureScraper
    from conad_scraper import ConadScraper
    from gigante_scraper import GiganteScraper
    from esselunga_scraper import EsselungaScraper

    scrapers = [
        ("conad", ConadScraper),
        ("gigante", GiganteScraper),
        ("esselunga", EsselungaScraper),
        ("conad_brochure", lambda: BrochureScraper("conad")),
        ("gigante_brochure", lambda: BrochureScraper("gigante")),
        ("esselunga_brochure", lambda: BrochureScraper("esselunga")),
    ]

    for label, cls in scrapers:
        try:
            s = cls() if callable(cls) else cls
            s.run()
        except Exception as e:
            print(f"\n=== {label} ===")
            print(f"  ERRORE: {e}")

    print("\n=== Pulizia offerte scadute ===")
    cleanup()

    print("\n=== Completato! ===")


if __name__ == "__main__":
    main()
