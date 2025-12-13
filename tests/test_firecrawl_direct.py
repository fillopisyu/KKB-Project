"""
Direct Firecrawl API Test
"""
import os
from dotenv import load_dotenv
load_dotenv()

try:
    from firecrawl import FirecrawlApp
except:
    try:
        from firecrawl import Firecrawl as FirecrawlApp
    except:
        print("HATA: firecrawl kutuphanesi yuklenemedi!")
        exit(1)

def test_firecrawl_direct():
    print("="*60)
    print("DIRECT FIRECRAWL API TEST")
    print("="*60)
    
    api_key = os.getenv("FIRECRAWL_API_KEY")
    print(f"\nAPI Key bulundu: {'EVET' if api_key else 'HAYIR'}")
    
    if not api_key:
        print("HATA: .env dosyasinda FIRECRAWL_API_KEY yok!")
        return
    
    print(f"API Key: {api_key[:10]}... (ilk 10 karakter)")
    
    test_url = "https://www.webtekno.com/"
    print(f"Test URL: {test_url}")
    print("\nFirecrawlApp baslatiliyor...")
    
    try:
        app = FirecrawlApp(api_key=api_key)
        print("FirecrawlApp baslatildi!")
        
        print(f"\nScraping: {test_url}")
        params = {'formats': ['markdown']}
        
        if hasattr(app, 'scrape_url'):
            result = app.scrape_url(test_url, params=params)
            print("scrape_url metodu kullanildi")
        elif hasattr(app, 'scrape'):
            result = app.scrape(test_url, params=params)
            print("scrape metodu kullanildi")
        else:
            print("HATA: Firecrawl scrape metodu bulunamadi!")
            return
        
        print(f"\nSonuc tipi: {type(result)}")
        
        if isinstance(result, dict):
            print(f"Dict keys: {list(result.keys())}")
            markdown = result.get('markdown', result.get('data', {}).get('markdown', ''))
        else:
            markdown = str(result)
        
        print(f"\nIcerik uzunlugu: {len(markdown)} karakter")
        print(f"\nIlk 300 karakter:")
        print("-"*60)
        print(markdown[:300])
        print("-"*60)
        
        print("\n" + "="*60)
        if len(markdown) > 100:
            print("BASARILI: Firecrawl calisiyor!")
        else:
            print("SORUN: Icerik cok kisa veya bos")
        print("="*60)
        
    except Exception as e:
        print(f"\nHATA: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_firecrawl_direct()
