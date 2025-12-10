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


def scrape_with_firecrawl(url):
    """
    Firecrawl API kullanarak verilen URL'i Markdown formatında çeker.
    Versiyon uyumsuzluklarına karşı dirençlidir.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")

    if not api_key:
        return "HATA: .env dosyasında FIRECRAWL_API_KEY bulunamadı."

    if not FirecrawlApp:
        return "HATA: 'firecrawl-py' kütüphanesi eksik. Lütfen 'pip install firecrawl-py' çalıştırın."

    print(f"🔥 Firecrawl Bağlanıyor: {url}...")

    try:
        app = FirecrawlApp(api_key=api_key)

        # --- VERSİYON KONTROLÜ VE METOT SEÇİMİ ---
        params = {'formats': ['markdown']}

        if hasattr(app, 'scrape_url'):
            # Standart v1.0+ yöntemi
            scrape_result = app.scrape_url(url, params=params)
        elif hasattr(app, 'scrape'):
            # Alternatif / Eski yöntem
            scrape_result = app.scrape(url, params=params)
        else:
            return "HATA: Firecrawl kütüphanesi yüklü ancak 'scrape_url' metodu bulunamadı. Lütfen 'pip install --upgrade firecrawl-py' yapın."

        # Sonucu Al
        # Bazen cevap direkt dict gelir, bazen obje olabilir.
        if isinstance(scrape_result, dict):
            content = scrape_result.get('markdown', '')
            # Eğer markdown yoksa data içindeki text'e bak
            if not content:
                content = scrape_result.get('data', {}).get('markdown', '')
        else:
            # Obje geldiyse
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

    def run_scraper(question, manual_urls=None):
        target_urls = manual_urls if manual_urls else URL_STORE

        if not target_urls:
            return "❌ HATA: Taranacak URL bulunamadı. Lütfen 'data/inputs/urls.txt' dosyasına link ekleyin."

        print(f"🌍 Web Kazıyıcı Çalışıyor... Hedef: {len(target_urls)} adres")
        results = []

        for url in target_urls:
            url = url.strip()
            if not url: continue

            print(f"   ↳ Hedef Taranıyor: {url}")

            # İçeriği Çek
            content = scrape_with_firecrawl(url)

            # Hata varsa rapora ekle
            if "Hata" in content or "UYARI" in content:
                results.append(f"❌ {url}: {content}")
                continue

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