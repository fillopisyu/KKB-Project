"""
Web Scraper Entegrasyon Testi
iPhone 15 ekran boyutu sorusunu test eder
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test URL ve soru - Webtekno.com - Street Fighter
TEST_URL = "https://www.webtekno.com/"
TEST_QUESTION = "Webtekno'da Street Fighter fragmanı hakkında bir haber var mı?"

print("=" * 60)
print("🧪 WEB SCRAPER ENTEGRASYON TESTİ")
print("=" * 60)
print(f"URL: {TEST_URL}")
print(f"Soru: {TEST_QUESTION}")
print("=" * 60)

# Import agents
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agents.web_scraper_trafilatura import get_web_scraper_agent
from utils.validators import should_use_web_scraper

print("\n1️⃣ Bileşenler yükleniyor...")

# Test 1: Web trigger check
print("\n2️⃣ Web trigger kontrolü...")
doc_response = "Doküman Yok"
data_response = "Veri Yok"

should_trigger = should_use_web_scraper(doc_response, data_response, TEST_QUESTION)
print(f"   Web trigger: {should_trigger}")

if not should_trigger:
    print("   ⚠️ WARNING: Web trigger FALSE - bu testte TRUE olmalı!")
    sys.exit(1)

# Test 2: Web scraper çağrısı
print("\n3️⃣ Firecrawl ile web scraping başlıyor...")
print(f"   URL: {TEST_URL}")

try:
    scraper = get_web_scraper_agent()
    web_content = scraper(
        question=TEST_QUESTION,
        manual_urls=[TEST_URL],
        use_crawl=False,  # Sadece ana sayfa
        max_depth=1,
        limit=1
    )
    
    print(f"\n4️⃣ Content alındı: {len(web_content)} karakter MARKDOWN")
    print(f"   İlk 200 karakter: {web_content[:200]}")
    
    # İçeriği dosyaya kaydet
    output_file = "tests/web_content_output.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"URL: {TEST_URL}\n")
        f.write(f"Soru: {TEST_QUESTION}\n")
        f.write(f"Uzunluk: {len(web_content)} karakter\n")
        f.write("="*60 + "\n")
        f.write(web_content)
    print(f"   📁 İçerik kaydedildi: {output_file}")
    
    # 5. LLM'E TÜM MARKDOWN VER, CEVAP AL
    print("\n5️⃣ LLM'e TÜM markdown veriliyor...")
    from core.config import llm_reasoning
    
    llm_prompt = f"""
    Aşağıdaki WEB içeriğine göre soruyu cevapla:
    
    SORU: {TEST_QUESTION}
    
    WEB İÇERİĞİ (MARKDOWN):
    {web_content}
    
    Kısa ve net cevap ver (maksimum 2 cümle).
    """
    
    print(f"   LLM'e gönderilen içerik: {len(web_content)} karakter")
    llm_answer = llm_reasoning.invoke(llm_prompt)
    
    print(f"\n📝 LLM CEVABI:")
    print(f"   {llm_answer.content}")
    
    print("\n✅ TEST BAŞARILI!")
    print(f"   ✅ Playwright → {len(web_content)} karakter markdown aldı")
    print(f"   ✅ LLM → TÜM markdown'ı gördü")
    print(f"   ✅ LLM → Cevap üretti")

except Exception as e:
    print(f"\n❌ TEST BAŞARISIZ!")
    print(f"   Hata: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("TEST TAMAMLANDI")
print("=" * 60)
