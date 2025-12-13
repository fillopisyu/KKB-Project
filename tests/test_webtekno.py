"""
Firecrawl Test - Webtekno Street Fighter
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.web_scraper import get_web_scraper_agent

def test_webtekno():
    print("="*60)
    print("FIRECRAWL TEST - Webtekno")
    print("="*60)
    
    test_question = "Street Fighter fragmani yayinlandi mi?"
    test_url = "https://www.webtekno.com/"
    
    print(f"\nSoru: {test_question}")
    print(f"URL: {test_url}")
    print("\n" + "-"*60)
    print("Firecrawl calistiriliyor...")
    print("-"*60 + "\n")
    
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
        print(result[:500])
        if len(result) > 500:
            print(f"\n... (+{len(result)-500} karakter daha)")
        
        print("\n" + "="*60)
        print("ANALIZ:")
        print("="*60)
        print(f"Icerik uzunlugu: {len(result)} karakter")
        
        # Checkler
        has_firecrawl = len(result) > 100
        has_answer = "Street Fighter" in result or "street fighter" in result.lower()
        has_source = "Kaynak:" in result or "webtekno" in result.lower()
        has_error = "HATA" in result or "Error" in result or "Scraping Hatası" in result
        
        print(f"Firecrawl calisti: {'EVET' if has_firecrawl else 'HAYIR'}")
        print(f"Street Fighter bulundu: {'EVET' if has_answer else 'HAYIR'}")
        print(f"Kaynak belirtildi: {'EVET' if has_source else 'HAYIR'}")
        print(f"Hata var: {'EVET' if has_error else 'HAYIR'}")
        
        print("\n" + "="*60)
        if has_firecrawl and not has_error:
            print("BASARILI: Firecrawl calisiyor!")
            if has_answer:
                print("  + Street Fighter bilgisi de bulundu!")
        elif has_error:
            print("HATA: Firecrawl hatasi!")
        else:
            print("SORUN: Icerik alinamadi")
        print("="*60)
        
    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_webtekno()
