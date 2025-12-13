"""
BASIT CACHE TEST - Log dosyasına yaz
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Log dosyasına yaz
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('tests/cache_test_log.txt', 'w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agents.web_scraper_trafilatura import get_web_scraper_agent

print("\n🧪 CACHE TEST BAŞLIYOR...")
print("="*60)

scraper = get_web_scraper_agent()

print("\n1️⃣ İLK ÇAĞRI (example.com):")
result1 = scraper("test soru", ["https://example.com/"])
print(f"   Sonuç: {len(result1)} karakter\n")

print("2️⃣ İKİNCİ ÇAĞRI (aynı URL, farklı soru):")
result2 = scraper("başka soru", ["https://example.com/"])
print(f"   Sonuç: {len(result2)} karakter\n")

print("="*60)
print("✅ Log dosyası: tests/cache_test_log.txt")
print("Kontrol et: 'Cache HIT' veya 'Cache MISS' ara!")
