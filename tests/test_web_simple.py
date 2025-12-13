"""
Simple Web Scraping Test - No Emojis
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.web_scraper import get_web_scraper_agent

def test_web_simple():
    print("="*60)
    print("WEB SCRAPING TEST")
    print("="*60)
    
    test_question = "Sirketin 2024 yili yonetim kurulu uyeleri kimlerdir?"
    test_url = "https://www.akbankinvestorrelations.com/tr/kurumsal-yonetim"
    
    print(f"\nSoru: {test_question}")
    print(f"URL: {test_url}")
    print("\nWeb scraper calistiriliyor...")
    
    try:
        scraper = get_web_scraper_agent()
        result = scraper(
            test_question,
            manual_urls=[test_url],
            use_crawl=False,
            max_depth=1,
            limit=1
        )
        
        print("\n" + "="*60)
        print("SONUC:")
        print("="*60)
        print(result[:300])
        if len(result) > 300:
            print(f"\n... ({len(result)-300} karakter daha)")
        
        print("\n" + "="*60)
        print("ANALIZ:")
        print("="*60)
        print(f"  Icerik uzunlugu: {len(result)} karakter")
        print(f"  Web'e gidildi: {'EVET' if len(result) > 50 else 'HAYIR'}")
        print(f"  Kaynak var: {'EVET' if 'Kaynak:' in result or 'KAYNAK' in result else 'HAYIR'}")
        print(f"  Hata var: {'EVET' if 'HATA' in result or 'Error' in result else 'HAYIR'}")
        
        print("\n" + "="*60)
        if len(result) > 100:
            print("BASARILI: Web scraper calisti!")
        else:
            print("KISMI: Web'e ulasti ama bilgi bulunamadi")
        print("="*60)
        
    except Exception as e:
        print(f"\nHATA: {e}")

if __name__ == "__main__":
    test_web_simple()
