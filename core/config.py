import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# --- KLOUDEKS AYARLARI ---
# Sizin .env dosyanızdaki isimleri kullanıyoruz:
KLOUDEKS_BASE_URL = os.getenv("MIA_BASE_URL")
API_KEY = os.getenv("MIA_API_KEY")

# Hata Kontrolü
if not API_KEY:
    raise ValueError("❌ HATA: .env dosyasında 'MIA_API_KEY' bulunamadı! Lütfen dosya isimlendirmelerini kontrol edin.")

if not KLOUDEKS_BASE_URL:
    # Eğer .env'de yoksa varsayılanı kullan
    KLOUDEKS_BASE_URL = "https://mia.csp.kloudeks.com/v1"

# --- 1. EMBEDDING MODELİ (Hafıza) ---
# Model: qwen3-embedding-8b (Boyut: 4096)
embedding_model = OpenAIEmbeddings(
    model="qwen3-embedding-8b",
    openai_api_key=API_KEY,
    openai_api_base=KLOUDEKS_BASE_URL,
    check_embedding_ctx_length=False
)

# --- 2. LLM MODELİ (Beyin) ---
# Model: gpt-oss-120b
llm_reasoning = ChatOpenAI(
    model="gpt-oss-120b",
    openai_api_key=API_KEY,
    openai_api_base=KLOUDEKS_BASE_URL,
    temperature=0,      # Denetçi olduğu için tutarlı olmalı
    max_tokens=4000     # Uzun cevaplar için alan
)

# --- SABİTLER ---
VECTOR_DB_PATH = os.path.join(os.getcwd(), "data", "chroma_db")


# --- UYGULAMA AYARLARI ---
class AppConfig:
    """Centralized application configuration"""
    
    # Agent settings
    MAX_PARALLEL_WORKERS = 5
    AGENT_TIMEOUT_SECONDS = 60
    
    # Web scraper defaults
    DEFAULT_CRAWL_DEPTH = 2
    DEFAULT_CRAWL_LIMIT = 10
    DEFAULT_USE_CRAWL = True
    
    # Retrieval settings
    DOC_RETRIEVAL_K = 5
    MIN_DOC_RESPONSE_LENGTH = 50
    MIN_DATA_RESPONSE_LENGTH = 20
    
    # Content limits
    WEB_CONTENT_MAX_CHARS = 40000
    SNIPPET_MAX_CHARS = 1000
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 70
    MEDIUM_CONFIDENCE_THRESHOLD = 40
    LOW_CONFIDENCE_THRESHOLD = 0