"""
WEB SCRAPER CACHE TEST
Embed işlemini doğrular
"""

import os
import sys
import logging
from dotenv import load_dotenv

# LOGGING SEVİYESİNİ YÜKSELT
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

# Test parametreleri
TEST_URL = "https://example.com/"  # Basit test için
TEST_QUESTION = "Bu sitede ne var?"

print("="*60)
print("🧪 WEB SCRAPER CACHE TEST")
print("="*60)
print(f"URL: {TEST_URL}")
print(f"Soru: {TEST_QUESTION}")
print("="*60)

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agents.web_scraper_trafilatura import get_web_scraper_agent

print("\n1️⃣ Agent yükleniyor...")
scraper = get_web_scraper_agent()

print("\n2️⃣ İLK ÇAĞRI - Cache MISS bekleniyor...")
print("-"*60)
result1 = scraper(
    question=TEST_QUESTION,
    manual_urls=[TEST_URL]
)
print("-"*60)
print(f"✅ İlk sonuç: {len(result1)} karakter")

print("\n3️⃣ İKİNCİ ÇAĞRI - Cache HIT bekleniyor...")
print("-"*60)
result2 = scraper(
    question="Farklı soru ama aynı URL",
    manual_urls=[TEST_URL]
)
print("-"*60)
print(f"✅ İkinci sonuç: {len(result2)} karakter")

print("\n4️⃣ SONUÇ:")
if "Cache HIT" in str(logging.getLogger().handlers):
    print("✅ CACHE ÇALIŞIYOR!")
else:
    print("⚠️ Cache log'ları terminal'de görünmeli")

print("\n" + "="*60)
print("TEST TAMAMLANDI")
print("Cache çalışıyor mu? Terminal log'larına bak!")
print("="*60)
