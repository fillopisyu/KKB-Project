"""
Web Scraper with PERSISTENT RAG + CACHE
BeautifulSoup + ChromaDB + Cache sistemi
"""

import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
import os

logger = logging.getLogger(__name__)


def scrape_with_beautifulsoup(url: str, timeout: int = 30) -> str:
    """BeautifulSoup ile web sayfasını scrape eder"""
    try:
        logger.info(f"📰 Scraping: {url}")
        
        import requests
        from bs4 import BeautifulSoup
        from markdownify import markdownify as md
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for tag in soup(["script", "style", "meta", "link", "noscript"]):
            tag.decompose()
        
        body = soup.body if soup.body else soup
        content = md(str(body), strip=['script', 'style'])
        
        if not content or len(content) < 100:
            return None
        
        logger.info(f"   ✅ {len(content)} karakter alındı")
        return content
        
    except Exception as e:
        logger.error(f"   ❌ Scraping hatası: {str(e)}")
        return None


def get_web_scraper_agent():
    """Web scraper agent (CACHE ile)"""
    
    def scraper_agent(question: str, manual_urls=None, **kwargs):
        """
        CACHE SİSTEMİ:
        1. URL zaten embed edilmiş mi kontrol et
        2. Edilmişse → Direkt search (HIZLI!)
        3. Edilmemişse → Scrape + Embed + Cache
        """
        if not manual_urls:
            logger.warning("Web scraper çağrıldı ama URL yok!")
            return "HATA: Taranacak URL belirtilmedi."
        
        # DUPLICATE URL'LERİ TEMİZLE
        unique_urls = list(set(manual_urls))
        if len(unique_urls) < len(manual_urls):
            logger.info(f"   🔄 Duplicate URL'ler temizlendi: {len(manual_urls)} → {len(unique_urls)}")
        
        logger.info(f"🌍 RAG Web Scraper (CACHE) başlıyor... Hedef: {len(unique_urls)} benzersiz URL")
        
        # KALICI ChromaDB (doc/data ile AYNI yerde)
        from core.config import embedding_model, VECTOR_DB_PATH
        
        try:
            vectorstore = Chroma(
                collection_name="web_content",
                embedding_function=embedding_model,
                persist_directory=VECTOR_DB_PATH  # AYNI YER!
            )
            logger.info(f"   📂 ChromaDB bağlantısı kuruldu (web_content @ {VECTOR_DB_PATH})")
        except Exception as e:
            logger.error(f"   ❌ ChromaDB hatası: {str(e)}")
            return "HATA: VectorStore oluşturulamadı."
        
        all_relevant_content = []
        
        for url in unique_urls:  # Deduplicated list
            logger.info(f"   ↳ İşleniyor: {url}")
            
            # CACHE KONTROLÜ
            try:
                existing_docs = vectorstore.get(
                    where={"source": url},
                    limit=1
                )
                
                if existing_docs and existing_docs['ids']:
                    # ✅ CACHE HIT - Zaten var!
                    logger.info(f"   ✅ Cache HIT! {url} zaten embed edilmiş")
                else:
                    # ❌ CACHE MISS - İlk kez, embed et!
                    logger.info(f"   📥 Cache MISS! {url} ilk kez scraping...")
                    
                    # 1. SCRAPE
                    content = scrape_with_beautifulsoup(url)
                    if not content:
                        logger.warning(f"   ⚠️ {url}: İçerik alınamadı")
                        continue
                    
                    # 2. CHUNK
                    logger.info(f"   📦 Chunk'lanıyor...")
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=200,
                        separators=["\n\n", "\n", ". ", " ", ""]
                    )
                    
                    chunks = text_splitter.create_documents(
                        texts=[content],
                        metadatas=[{"source": url}]
                    )
                    
                    logger.info(f"   ✅ {len(chunks)} chunk oluşturuldu")
                    
                    # 3. EMBED + CACHE'E EKLE
                    logger.info(f"   💾 Embedding + Cache'e ekleniyor...")
                    vectorstore.add_documents(chunks)
                    logger.info(f"   ✅ {url} cache'e eklendi (KALICI)")
                
                # 4. SIMILARITY SEARCH (her ikisinde de)
                logger.info(f"   🔍 Soruyla ilgili chunk'lar aranıyor...")
                relevant_docs = vectorstore.similarity_search(
                    question,
                    k=5,
                    filter={"source": url}
                )
                
                logger.info(f"   ✅ {len(relevant_docs)} alakalı chunk bulundu")
                
                # 5. FORMAT
                if relevant_docs:
                    relevant_text = "\n\n".join([
                        f"[Chunk {i+1}] {doc.page_content}" 
                        for i, doc in enumerate(relevant_docs)
                    ])
                    
                    # Kaynak formatını diğer ajanlarla tutarlı hale getir
                    all_relevant_content.append(f"\n\n[Kaynak: {url}]\n{relevant_text}\n")
                
            except Exception as e:
                logger.error(f"   ❌ İşlem hatası ({url}): {str(e)}")
                continue
        
        if not all_relevant_content:
            return "UYARI: Hiçbir URL'den alakalı içerik bulunamadı."
        
        combined = "\n".join(all_relevant_content)
        logger.info(f"✅ Toplam {len(combined)} karakter alakalı içerik (RAG + CACHE)")
        
        return combined
    
    return scraper_agent
