"""
Trafilatura Web Scraper
En iyi içerik çıkarma kütüphanesi - otomatik temizleme
"""

import logging
import trafilatura

logger = logging.getLogger(__name__)


def scrape_with_trafilatura(url: str, timeout: int = 30) -> str:
    """
    Trafilatura ile web sayfasını scrape eder
    
    Args:
        url: Scrape edilecek URL
        timeout: Request timeout (saniye)
    
    Returns:
        str: Sayfa içeriği (markdown formatında)
    """
    try:
        logger.info(f"📰 Trafilatura ile scraping başlıyor: {url}")
        
        # Sayfayı indir
        logger.info(f"   HTTP GET yapılıyor...")
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            logger.error(f"   ❌ Sayfa indirilemedi")
            return "UYARI: Sayfa indirilemedi."
        
        # Ana içeriği çıkar (markdown formatında)
        logger.info(f"   İçerik çıkarılıyor...")
        content = trafilatura.extract(
            downloaded,
            output_format='markdown',
            include_links=True,
            include_images=False,
            include_tables=True
        )
        
        if not content or len(content) < 100:
            logger.warning(f"   Çok az içerik: {len(content) if content else 0} karakter")
            return "UYARI: Sayfa içeriği çok kısa veya boş."
        
        logger.info(f"   ✅ {len(content)} karakter markdown alındı")
        return content
        
    except Exception as e:
        logger.error(f"   ❌ Trafilatura hatası: {type(e).__name__}: {str(e)}")
        return f"Scraping Hatası: {str(e)}"


def get_web_scraper_agent():
    """Web scraper agent'ını döndürür (Trafilatura ile)"""
    
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
        
        logger.info(f"🌍 Trafilatura Web Scraper başlıyor... Hedef: {len(manual_urls)} URL")
        
        all_content = []
        
        for url in manual_urls:
            logger.info(f"   ↳ Taranıyor: {url}")
            content = scrape_with_trafilatura(url)
            
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
