"""
End-to-End Web Scraping Test
Gerçekten Firecrawl ile web'e gidip içerik çekiyor mu?
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.web_scraper import get_web_scraper_agent

def test_real_web_scraping():
    """Test actual web scraping with Firecrawl."""
    print("=" * 70)
    print("TEST: Gerçek Web Scraping - Firecrawl ile URL'den içerik çekme")
    print("=" * 70)
    
    # Test sorusu: Belgelerde OLMAYAN bir şey
    test_question = "Şirketin 2024 yılı yönetim kurulu üyeleri kimlerdir?"
    
    # Test URL
    test_url = "https://www.akbankinvestorrelations.com/tr/kurumsal-yonetim"
    
    print(f"\n📋 Test Sorusu: {test_question}")
    print(f"🌐 Hedef URL: {test_url}")
    print(f"📍 Mod: SCRAPE (tek sayfa, crawl yok)")
    print("\n" + "-" * 70)
    print("🚀 Web scraper çağrılıyor...")
    print("-" * 70)
    
    try:
        # Get web scraper agent
        scraper = get_web_scraper_agent()
        
        # Call with real URL
        result = scraper(
            test_question,
            manual_urls=[test_url],
            use_crawl=False,  # Sadece scrape, daha hızlı
            max_depth=1,
            limit=1
        )
        
        # Results
        print("\n" + "=" * 70)
        print("📄 WEB SCRAPER SONUCU:")
        print("=" * 70)
        
        # İlk 500 karakter göster
        preview = result[:500] if len(result) > 500 else result
        print(preview)
        if len(result) > 500:
            print(f"\n... ({len(result) - 500} karakter daha var)")
        
        print("\n" + "=" * 70)
        print("🔍 SONUÇ ANALİZİ:")
        print("=" * 70)
        
        # Check indicators
        has_content = len(result) > 100
        has_source_ref = "Kaynak:" in result or "KAYNAK" in result
        has_url_ref = test_url in result or "akbank" in result.lower()
        no_error = not any(x in result for x in ["HATA", "Error", "bilgi yok", "bulunamadı"])
        
        print(f"  ✓ İçerik uzunluğu: {len(result)} karakter")
        print(f"  {'✅' if has_content else '❌'} Yeterli içerik (>100 char)")
        print(f"  {'✅' if has_source_ref else '❌'} Kaynak referansı var")
        print(f"  {'✅' if has_url_ref else '❌'} URL/site adı geçiyor")
        print(f"  {'✅' if no_error else '❌'} Hata mesajı yok")
        
        # Final verdict
        print("\n" + "=" * 70)
        if has_content and has_source_ref and no_error:
            print("✅ TEST BAŞARILI!")
            print("\nKanıt:")
            print("  • Firecrawl ile web'e gitti ✓")
            print("  • İçerik çekildi ve analiz edildi ✓")
            print("  • LLM cevap üretti ✓")
            print("  • Kaynak gösterildi ✓")
        elif has_content and not no_error:
            print("⚠️ TEST KISMİ BAŞARILI")
            print("\nDurum:")
            print("  • Web'e gidildi ✓")
            print("  • Ama soruya cevap bulunamadı (normal olabilir)")
        else:
            print("❌ TEST BAŞARISIZ")
            print("\nSorun:")
            print(f"  • İçerik var: {has_content}")
            print(f"  • Kaynak ref: {has_source_ref}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ TEST BAŞARISIZ - HATA:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_web_scraping()
