import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.config import llm_reasoning
from dotenv import load_dotenv

# Link Deposunu İmport Ediyoruz
from ingestion.processor import URL_STORE

# .env yükle
load_dotenv()

# Firecrawl Kütüphanesi Kontrolü
try:
    from firecrawl import FirecrawlApp
except ImportError:
    try:
        # Bazı versiyonlarda class ismi sadece Firecrawl olabilir
        from firecrawl import Firecrawl as FirecrawlApp
    except ImportError:
        FirecrawlApp = None


def scrape_with_firecrawl(url, use_crawl=False, max_depth=2, limit=10):
    """
    Firecrawl API kullanarak verilen URL'i Markdown formatında çeker.
    
    Args:
        url: Hedef URL
        use_crawl: True ise tüm alt sayfaları da tarar (crawl), False ise sadece tek sayfa (scrape)
        max_depth: Crawl derinliği (kaç seviye link takip edilecek)
        limit: Maksimum taranacak sayfa sayısı
    
    Returns:
        Tek sayfa için: Markdown string
        Crawl için: Dict with {'pages': [{'url': ..., 'markdown': ...}, ...]}
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")

    if not api_key:
        return "HATA: .env dosyasında FIRECRAWL_API_KEY bulunamadı."

    if not FirecrawlApp:
        return "HATA: 'firecrawl-py' kütüphanesi eksik. Lütfen 'pip install firecrawl-py' çalıştırın."

    try:
        app = FirecrawlApp(api_key=api_key)

        # --- CRAWL MODE (Alt sayfaları da tara) ---
        if use_crawl:
            print(f"🕷️ Firecrawl CRAWLING: {url} (Derinlik: {max_depth}, Limit: {limit})...")
            
            crawl_params = {
                'limit': limit,
                'scrapeOptions': {'formats': ['markdown']},
                'maxDepth': max_depth
            }
            
            # Crawl metodu kontrolü
            if hasattr(app, 'crawl_url'):
                crawl_result = app.crawl_url(url, params=crawl_params)
            elif hasattr(app, 'crawl'):
                crawl_result = app.crawl(url, params=crawl_params)
            else:
                return "HATA: Firecrawl kütüphanesi 'crawl_url' metodunu desteklemiyor. Lütfen güncelleyin."
            
            # Sonuçları işle
            if isinstance(crawl_result, dict):
                pages = crawl_result.get('data', [])
                if not pages:
                    return "UYARI: Crawl sonucu boş döndü."
                
                # Her sayfanın markdown içeriğini çıkar
                processed_pages = []
                for page in pages:
                    page_url = page.get('url', url)
                    markdown = page.get('markdown', '')
                    if markdown:
                        processed_pages.append({
                            'url': page_url,
                            'markdown': markdown
                        })
                
                print(f"   ✅ {len(processed_pages)} sayfa tarandı.")
                return {'pages': processed_pages}
            else:
                return "HATA: Crawl sonucu beklenmeyen formatta."

        # --- SCRAPE MODE (Sadece tek sayfa) ---
        else:
            print(f"🔥 Firecrawl SCRAPING: {url}...")
            
            params = {'formats': ['markdown']}

            if hasattr(app, 'scrape_url'):
                scrape_result = app.scrape_url(url, params=params)
            elif hasattr(app, 'scrape'):
                scrape_result = app.scrape(url, params=params)
            else:
                return "HATA: Firecrawl kütüphanesi yüklü ancak 'scrape_url' metodu bulunamadı."

            # Sonucu Al
            if isinstance(scrape_result, dict):
                content = scrape_result.get('markdown', '')
                if not content:
                    content = scrape_result.get('data', {}).get('markdown', '')
            else:
                content = str(scrape_result)

            if not content:
                return "UYARI: Web sayfası boş döndü veya erişim engellendi."

            return content

    except Exception as e:
        return f"Scraping Hatası ({url}): {str(e)}"


def get_web_scraper_agent():
    """
    URL listesini tarayıp soruyu cevaplayan akıllı fonksiyonu döndürür.
    """

    # --- LLM ANALİZ ZİNCİRİ ---
    prompt = ChatPromptTemplate.from_template("""
    Sen uzman bir "Dijital İçerik Analistisin".
    Sana bir web sayfasının ham içeriği (Markdown formatında) verilecek.

    SORU: {question}

    WEB SAYFASI İÇERİĞİ:
    {web_content}

    GÖREVİN:
    Sadece yukarıdaki web içeriğini kullanarak soruyu cevapla.

    KURALLAR:
    1. **SADECE BU İÇERİK:** Asla kendi genel bilgini kullanma. Cevap metinde yoksa "Bu sayfada bilgi yok" de.
    2. **KANIT GÖSTER:** Cevabı bulursan, metinden alıntı yap ve sonuna "(Kaynak: [Web Sitesi])" ekle.
    3. **ÖZETLE:** Cevabı gereksiz detaylardan arındırarak net bir şekilde ver.
    """)

    chain = prompt | llm_reasoning | StrOutputParser()

    def run_scraper(question, manual_urls=None, use_crawl=True, max_depth=2, limit=10):
        """
        Web scraper agent'ı çalıştırır.
        
        Args:
            question: Sorulacak soru
            manual_urls: Manuel URL listesi (opsiyonel)
            use_crawl: True ise alt sayfaları da tarar, False ise sadece ana sayfa
            max_depth: Crawl derinliği
            limit: Maksimum taranacak sayfa sayısı
        """
        target_urls = manual_urls if manual_urls else URL_STORE

        if not target_urls:
            return "❌ HATA: Taranacak URL bulunamadı. Lütfen 'data/inputs/urls.txt' dosyasına link ekleyin."

        mode_text = "CRAWLING (Alt sayfalar dahil)" if use_crawl else "SCRAPING (Sadece ana sayfa)"
        print(f"🌍 Web Kazıyıcı Çalışıyor... Mod: {mode_text}, Hedef: {len(target_urls)} adres")
        results = []

        for url in target_urls:
            url = url.strip()
            if not url: continue

            print(f"   ↳ Hedef Taranıyor: {url}")

            # İçeriği Çek (Crawl veya Scrape)
            content = scrape_with_firecrawl(url, use_crawl=use_crawl, max_depth=max_depth, limit=limit)

            # Hata kontrolü
            if isinstance(content, str) and ("HATA" in content or "UYARI" in content):
                results.append(f"❌ {url}: {content}")
                continue

            # --- CRAWL MODE: Birden fazla sayfa ---
            if use_crawl and isinstance(content, dict) and 'pages' in content:
                pages = content['pages']
                print(f"      📄 {len(pages)} sayfa bulundu, analiz ediliyor...")
                
                page_results = []
                for page in pages:
                    page_url = page['url']
                    page_content = page['markdown']
                    
                    # İçeriği kırp
                    trimmed_content = page_content[:40000]
                    
                    # LLM Analizi
                    try:
                        answer = chain.invoke({
                            "question": question,
                            "web_content": trimmed_content
                        })

                        if "bilgi yok" not in answer.lower() and "bulunmamaktadır" not in answer.lower():
                            page_results.append(f"📄 {page_url}:\n{answer}")
                        else:
                            print(f"         ℹ️ {page_url} - Bilgi yok")

                    except Exception as e:
                        page_results.append(f"Analiz Hatası ({page_url}): {e}")
                
                if page_results:
                    results.append(f"✅ KAYNAK GRUBU ({url}):\n" + "\n\n".join(page_results))
                else:
                    print(f"      ℹ️ Hiçbir sayfada bilgi bulunamadı.")

            # --- SCRAPE MODE: Tek sayfa ---
            else:
                if isinstance(content, str):
                    # İçeriği Kırp
                    trimmed_content = content[:40000]

                    # LLM Analizi
                    try:
                        answer = chain.invoke({
                            "question": question,
                            "web_content": trimmed_content
                        })

                        if "bilgi yok" not in answer.lower() and "bulunmamaktadır" not in answer.lower():
                            results.append(f"✅ KAYNAK ({url}):\n{answer}")
                        else:
                            print(f"      ℹ️ Bu sayfada bilgi çıkmadı.")

                    except Exception as e:
                        results.append(f"Analiz Hatası ({url}): {e}")

        if not results:
            return "Taranan web sayfalarında bu soruyla ilgili spesifik bir bilgi bulunamadı."

        return "\n\n---\n\n".join(results)

    return run_scraper