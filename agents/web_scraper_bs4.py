"""
BeautifulSoup Web Scraper
Windows + Streamlit uyumlu, Playwright yerine
"""

import logging
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


def scrape_with_beautifulsoup(url: str, timeout: int = 30) -> str:
    """
    BeautifulSoup ile web sayfasını scrape eder
    
    Args:
        url: Scrape edilecek URL
        timeout: Request timeout (saniye)
    
    Returns:
        str: Sayfa içeriği (markdown formatında)
    """
    try:
        logger.info(f"🥣 BeautifulSoup ile scraping başlıyor: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Sayfayı al
        logger.info(f"   HTTP GET yapılıyor...")
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # HTML parse
        logger.info(f"   HTML parse ediliyor...")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Script ve style etiketlerini temizle
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
        
        # Ana içeriği bul
        content = None
        selectors = ['main', 'article', '#content', '.content', 'body']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                content = element
                logger.info(f"   İçerik bulundu: {selector}")
                break
        
        if not content:
            content = soup.body if soup.body else soup
            logger.info(f"   Fallback: body kullanıldı")
        
        # HTML → Markdown
        logger.info(f"   HTML → Markdown dönüşümü...")
        markdown_content = md(str(content))
        
        if len(markdown_content) < 100:
            logger.warning(f"   Çok az içerik: {len(markdown_content)} karakter")
            return "UYARI: Sayfa içeriği çok kısa veya boş."
        
        logger.info(f"   ✅ {len(markdown_content)} karakter markdown alındı")
        return markdown_content
        
    except requests.Timeout:
        logger.error(f"   ❌ Timeout: {url}")
        return f"Scraping Hatası: Timeout ({timeout}s)"
    except requests.RequestException as e:
        logger.error(f"   ❌ Request hatası: {type(e).__name__}: {str(e)}")
        return f"Scraping Hatası: {str(e)}"
    except Exception as e:
        logger.error(f"   ❌ BeautifulSoup hatası: {type(e).__name__}: {str(e)}")
        return f"Scraping Hatası: {str(e)}"


def get_web_scraper_agent():
    """Web scraper agent'ını döndürür (BeautifulSoup ile)"""
    
    def scraper_agent(question: str, manual_urls=None, **kwargs):
        """
        Soruyu web'den cevaplamak için URL'leri scrape eder
        
        Args:
            question: Sorulacak soru
            manual_urls: Taranacak URL listesi
            **kwargs: Ek parametreler (kullanılmıyor)
        
        Returns:
            str: Tüm URL'lerden toplanan içerik
        """
        if not manual_urls:
            logger.warning("Web scraper çağrıldı ama URL yok!")
            return "HATA: Taranacak URL belirtilmedi."
        
        logger.info(f"🌍 BeautifulSoup Web Scraper başlıyor... Hedef: {len(manual_urls)} URL")
        
        all_content = []
        
        for url in manual_urls:
            logger.info(f"   ↳ Taranıyor: {url}")
            content = scrape_with_beautifulsoup(url)
            
            if content and not content.startswith("HATA") and not content.startswith("UYARI"):
                all_content.append(f"\n\n=== {url} ===\n{content}\n")
            else:
                logger.warning(f"   ⚠️ {url}: İçerik alınamadı")
        
        if not all_content:
            return "UYARI: Hiçbir URL'den içerik alınamadı."
        
        combined = "\n".join(all_content)
        logger.info(f"✅ Toplam {len(combined)} karakter içerik toplandı")
        
        return combined
    
    return scraper_agent
