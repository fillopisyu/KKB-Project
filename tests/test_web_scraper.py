"""
Web Scraper Test - Firecrawl entegrasyonunu test et
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.web_scraper import get_web_scraper_agent

def test_web_scraper():
    """Test if web scraper works with a simple question."""
    print("=" * 60)
    print("TEST: Web Scraper - Firecrawl")
    print("=" * 60)
    
    # Test question
    test_question = "Şirketin sürdürülebilirlik hedefleri nedir?"
    
    # Test URL (Akbank investor relations)
    test_urls = ["https://www.akbankinvestorrelations.com"]
    
    print(f"\n📋 Test Sorusu: {test_question}")
    print(f"🌐 Test URL: {test_urls[0]}")
    print("\n🔍 Web Scraper çağrılıyor...")
    
    try:
        # Get web scraper agent
        scraper = get_web_scraper_agent()
        
        # Call with test question
        result = scraper(
            test_question, 
            manual_urls=test_urls,
            use_crawl=False,  # Sadece scrape, crawl değil (daha hızlı)
            max_depth=1,
            limit=3
        )
        
        print("\n📄 Web Scraper Sonucu:")
        print("-" * 60)
        print(result[:500] if len(result) > 500 else result)
        print("-" * 60)
        
        # Check for success indicators
        has_content = len(result) > 100
        has_source = "Kaynak:" in result or "kaynak:" in result
        no_error = "Hata" not in result and "Error" not in result
        
        print("\n🔎 Sonuç Kontrolü:")
        print(f"   İçerik var (>100 char): {'✅' if has_content else '❌'} ({len(result)} karakter)")
        print(f"   Kaynak referansı var: {'✅' if has_source else '❌'}")
        print(f"   Hata yok: {'✅' if no_error else '⚠️'}")
        
        print("\n" + "=" * 60)
        if has_content and no_error:
            print("✅ TEST BAŞARILI: Web scraper çalışıyor!")
        else:
            print("⚠️ TEST UYARI: Scraper çalıştı ama sonuç beklenen gibi değil")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST BAŞARISIZ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_web_scraper()
