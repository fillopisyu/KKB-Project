import os
import pandas as pd
from typing import List, Dict, Set
import logging

# Suppress verbose output from third-party libraries
# This prevents "Need to load profiles" and similar messages from Unstructured
logging.getLogger("unstructured").setLevel(logging.WARNING)
logging.getLogger("unstructured_inference").setLevel(logging.WARNING)
logging.getLogger("unstructured.partition").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.WARNING)

# LangChain Yükleyicileri
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredExcelLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    TextLoader
)

# Try to import the new UnstructuredLoader, fallback to old one if not available
try:
    from langchain_unstructured import UnstructuredLoader
    USE_NEW_UNSTRUCTURED = True
except ImportError:
    from langchain_community.document_loaders import UnstructuredFileLoader
    USE_NEW_UNSTRUCTURED = False
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='langchain_community')

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.config import embedding_model, VECTOR_DB_PATH, llm_reasoning

# --- GLOBAL DEPOLAR ---
# Bu listeler hafızada (RAM) tutulur. Ajanlar buradan okur.
STRUCTURED_STORE: Dict[str, List[str]] = {}
URL_STORE: List[str] = []


def get_existing_vector_sources() -> Set[str]:
    """Vektör DB'de zaten var olan dosyaları listeler."""
    if not os.path.exists(VECTOR_DB_PATH): return set()
    try:
        db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding_model)
        data = db.get()
        sources = set()
        if data and 'metadatas' in data:
            for meta in data['metadatas']:
                if meta and 'source' in meta: sources.add(meta['source'])
        return sources
    except:
        return set()


# --- 1. AKILLI SNIPPET (ÖNİZLEME) ALICI ---
def get_file_snippet(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    snippet = ""
    try:
        # Tablolar için özel okuma (Boşlukları atla)
        if ext in ['.csv', '.xlsx', '.xls']:
            if ext == '.csv':
                df = pd.read_csv(file_path, nrows=40, on_bad_lines='skip', header=None)
            else:
                df = pd.read_excel(file_path, nrows=40, header=None)

            df_clean = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
            if not df_clean.empty:
                snippet = df_clean.head(10).to_string(index=False)
            else:
                snippet = "Tablo yapısı var ama içi boş."

        # Metin dosyası (URL listesi olabilir mi?)
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(500)
                if "http" in content:
                    snippet = "İçerik bir URL listesine benziyor: " + content
                else:
                    snippet = content

        # Diğer tüm formatlar için UnstructuredLoader (Joker)
        else:
            if USE_NEW_UNSTRUCTURED:
                loader = UnstructuredLoader(file_path)
            else:
                loader = UnstructuredFileLoader(file_path)
            docs = loader.load()
            if docs:
                # İlk 1000 karakteri al
                snippet = docs[0].page_content[:1000].strip()

    except Exception as e:
        snippet = f"Okuma hatası: {str(e)}"

    return snippet


# --- 2. LLM KARAR MEKANİZMASI ---
def decide_strategy_with_llm(file_name: str, snippet: str) -> str:
    print(f"🤖 Analiz Ediliyor: {file_name}")

    # URL Kontrolü (Manuel Override - Hız için)
    if "urls.txt" in file_name.lower() or "http" in snippet:
        print("   ↳ Karar: URL_LIST (Otomatik Tespit)")
        return "URL_LIST"

    # Detaylı ve Net Prompt
    prompt = ChatPromptTemplate.from_template("""
    Sen uzman bir Veri Mühendisisin.
    Sana bir dosyanın ismi ve içeriğinin başından küçük bir parça (snippet) verilecek.
    Görevin, bu dosyanın nasıl işlenmesi gerektiğine karar vermektir.

    DOSYA ADI: {file_name}
    İÇERİK ÖZETİ:
    {snippet}

    KARAR KURALLARI:
    1. "STRUCTURED": Eğer içerik satır ve sütunlardan oluşan bir tablo, veri seti, finansal liste, Excel, CSV veya JSON verisi ise. (Sayısal analiz yapılmalı).
    2. "VECTOR": Eğer içerik düz metin, rapor, makale, politika dokümanı, sözleşme, e-posta veya açıklama metni ise. (Anlamsal arama yapılmalı).
    3. "URL_LIST": Eğer içerik sadece web linklerinden (http/https) oluşuyorsa.

    Sadece "STRUCTURED", "VECTOR" veya "URL_LIST" cevabını ver. Başka hiçbir şey yazma.
    """)

    try:
        chain = prompt | llm_reasoning | StrOutputParser()
        decision = chain.invoke({"file_name": file_name, "snippet": snippet}).strip().upper()
    except:
        decision = "VECTOR"  # Hata olursa varsayılan

    # Güvenlik: LLM saçmalarsa uzantıya dön
    if decision not in ["STRUCTURED", "VECTOR", "URL_LIST"]:
        ext = os.path.splitext(file_name)[1].lower()
        if ext in ['.xlsx', '.xls', '.csv', '.json']: return "STRUCTURED"
        return "VECTOR"

    print(f"   ↳ Karar: {decision}")
    return decision


# --- 3. İŞLEME FONKSİYONLARI ---
def process_url_list(file_path):
    """Metin dosyasındaki linkleri okur ve hafızaya atar."""
    # KRİTİK: global değişkeni 'extend' ile güncelleyeceğiz
    global URL_STORE
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Sadece http ile başlayan temiz satırları al
            urls = [line.strip() for line in f.readlines() if line.strip().startswith("http")]

        if urls:
            # Duplicate (Tekrar) kontrolü
            current_urls = set(URL_STORE)
            new_urls = [u for u in urls if u not in current_urls]

            if new_urls:
                # Ekleme yapıyoruz (Listeyi sıfırlamıyoruz)
                URL_STORE.extend(new_urls)
                print(f"   🔗 {len(new_urls)} yeni Web Adresi hafızaya alındı.")
            else:
                print("   🔗 Linkler zaten hafızada mevcut.")
        else:
            print("   ⚠️ Dosyada geçerli URL bulunamadı.")

    except Exception as e:
        print(f"   ❌ URL Okuma Hatası: {e}")


def process_vector(file_path, file_name, ext):
    """Vektör DB için işler"""
    chunks = []
    try:
        # Özel Yükleyiciler (Kalite için)
        if ext == '.pdf':
            loader = PyPDFLoader(file_path)
        elif ext in ['.docx', '.doc']:
            loader = UnstructuredWordDocumentLoader(file_path)
        elif ext == '.pptx':
            loader = UnstructuredPowerPointLoader(file_path)
        elif ext in ['.txt', '.md', '.py', '.xml', '.html']:
            loader = TextLoader(file_path, encoding='utf-8', autodetect_encoding=True)

        # Bilinmeyen Formatlar (Joker)
        else:
            print(f"   ⚠️ Bilinmeyen format ({ext}), 'Unstructured' ile deneniyor...")
            if USE_NEW_UNSTRUCTURED:
                loader = UnstructuredLoader(file_path)
            else:
                loader = UnstructuredFileLoader(file_path)

        raw_docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_documents(raw_docs)
        for c in chunks: c.metadata["source"] = file_name
        print(f"   ✅ {len(chunks)} parça metin çıkarıldı.")

    except Exception as e:
        print(f"   ❌ Vektör İşleme Hatası ({file_name}): {e}")

    return chunks


def process_structured(file_path, file_name, ext):
    """Data Agent için işler"""
    html_tables = []
    try:
        if ext in ['.xlsx', '.xls']:
            loader = UnstructuredExcelLoader(file_path, mode="elements")
            for doc in loader.load():
                if 'text_as_html' in doc.metadata:
                    html_tables.append(doc.metadata['text_as_html'])
        elif ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8-sig', on_bad_lines='skip')
            html_tables.append(df.to_html(index=False))
        elif ext == '.json':
            df = pd.read_json(file_path)
            html_tables.append(df.to_html(index=False))

        if html_tables:
            STRUCTURED_STORE[file_name] = html_tables
            print(f"   ✅ {len(html_tables)} tablo hafızaya alındı.")
    except Exception as e:
        print(f"   ❌ Yapısal Hata: {e}")


# --- ANA YÖNETİCİ ---
def ingest_files(file_paths: List[str]):
    existing_vectors = get_existing_vector_sources()
    vector_batch = []

    print(f"\n🔄 Akıllı Yükleyici ({len(file_paths)} dosya)...")

    for path in file_paths:
        file_name = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()

        # 1. Snippet Al
        snippet = get_file_snippet(path)

        # 2. LLM Karar Versin
        strategy = decide_strategy_with_llm(file_name, snippet)

        # 3. Uygula
        if strategy == "VECTOR":
            if file_name in existing_vectors:
                print(f"⏩ {file_name} zaten var.")
                continue
            chunks = process_vector(path, file_name, ext)
            vector_batch.extend(chunks)

        elif strategy == "STRUCTURED":
            process_structured(path, file_name, ext)

        elif strategy == "URL_LIST":
            process_url_list(path)

    # Toplu Vektör Kaydı
    if vector_batch:
        print(f"🚀 {len(vector_batch)} parça Vektör DB'ye yazılıyor...")
        try:
            Chroma.from_documents(vector_batch, embedding_model, persist_directory=VECTOR_DB_PATH)
            print("🎉 Vektör DB Güncellendi!")
        except Exception as e:
            print(f"❌ DB Hatası: {e}")