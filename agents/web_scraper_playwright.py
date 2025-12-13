"""
Playwright Web Scraper
Firecrawl yerine Playwright kullanarak web scraping yapar
"""

import logging
from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
import time

logger = logging.getLogger(__name__)


def scrape_with_playwright(url: str, wait_time: int = 3000, timeout: int = 60000) -> str:
    """
    Playwright ile web sayfasını scrape eder
    
    Args:
        url: Scrape edilecek URL
        wait_time: Sayfa yükleme bekleme süresi (ms)
        timeout: Maksimum bekleme süresi (ms) - varsayılan 60 saniye
    
    Returns:
        str: Sayfa içeriği (markdown formatında)
    """
    try:
        logger.info(f"🎭 Playwright ile scraping başlıyor: {url}")
        
        with sync_playwright() as p:
            # Chromium browser başlat
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            # Sayfayı yükle (artırılmış timeout)
            logger.info(f"   Sayfa yükleniyor (timeout: {timeout}ms)...")
            page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            
            # JavaScript'in render olması için bekle
            page.wait_for_timeout(wait_time)
            
            # Ana içeriği al - HTML olarak
            content_selectors = [
                'main',
                'article', 
                '#content',
                '.content',
                'body'
            ]
            
            content_html = None
            for selector in content_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        content_html = element.inner_html()  # HTML al
                        logger.info(f"   İçerik bulundu: {selector}")
                        break
                except:
                    continue
            
            # Fallback: Tüm body
            if not content_html:
                content_html = page.inner_html('body')
                logger.info(f"   Fallback: body kullanıldı")
            
            browser.close()
            
            if not content_html or len(content_html) < 100:
                logger.warning(f"   Çok az içerik: {len(content_html)} karakter")
                return "UYARI: Sayfa içeriği çok kısa veya boş."
            
            # HTML'i Markdown'a çevir
            logger.info(f"   HTML -> Markdown dönüşümü yapılıyor...")
            markdown_content = md(content_html, strip=['script', 'style'])
            
            logger.info(f"   ✅ {len(markdown_content)} karakter markdown alındı")
            return markdown_content
            
    except Exception as e:
        logger.error(f"   ❌ Playwright hatası: {type(e).__name__}: {str(e)}")
        return f"Scraping Hatası: {str(e)}"


def get_web_scraper_agent():
    """Web scraper agent'ını döndürür (Playwright ile)"""
    
    def scraper_agent(question: str, manual_urls=None, **kwargs):
        """
        Soruyu web'den cevaplamak için URL'leri scrape eder
        
        Args:
            question: Sorulacak soru
            manual_urls: Taranacak URL listesi
            **kwargs: Ek parametreler (use_crawl, max_depth vb - şimdilik kullanılmıyor)
        
        Returns:
            str: Tüm URL'lerden toplanan içerik
        """
        if not manual_urls:
            logger.warning("Web scraper çağrıldı ama URL yok!")
            return "HATA: Taranacak URL belirtilmedi."
        
        logger.info(f"🌍 Playwright Web Scraper başlıyor... Hedef: {len(manual_urls)} URL")
        
        all_content = []
        
        for url in manual_urls:
            logger.info(f"   ↳ Taranıyor: {url}")
            content = scrape_with_playwright(url)
            
            if content and not content.startswith("HATA") and not content.startswith("UYARI"):
                # Kaynak formatını diğer ajanlarla tutarlı hale getir
                all_content.append(f"\n\n[Kaynak: {url}]\n{content}\n")
            else:
                logger.warning(f"   ⚠️ {url}: İçerik alınamadı")
        
        if not all_content:
            return "UYARI: Hiçbir URL'den içerik alınamadı."
        
        combined = "\n".join(all_content)
        logger.info(f"✅ Toplam {len(combined)} karakter içerik toplandı")
        
        return combined
    
    return scraper_agent
