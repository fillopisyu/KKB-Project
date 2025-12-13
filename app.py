import streamlit as st
import os
import time
import json
import concurrent.futures
from datetime import datetime
from langchain_core.messages import HumanMessage
from agents.data_agent import get_data_agent
from agents.doc_agent import get_doc_agent
from agents.web_scraper import get_web_scraper_agent
from agents.evaluator import evaluate_answer
from ingestion.processor import ingest_files
from core.config import llm_reasoning, AppConfig
from core.logger import logger
from core.unit_converter import validate_and_convert_answer
from utils.validators import should_use_web_scraper, validate_ai_response, validate_question_structure
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from dotenv import load_dotenv

# Fix for ThreadPoolExecutor context warnings
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except ImportError:
    # Fallback for older Streamlit versions
    add_script_run_ctx = None
    get_script_run_ctx = None

load_dotenv()

# Suppress harmless ScriptRunContext warnings from ThreadPoolExecutor
import logging
logging.getLogger("streamlit.runtime.scriptrunner.script_runner").setLevel(logging.ERROR)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Greendeks | KKB Dark",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PREMIUM KKB DARK CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        color: #e2e8f0;
    }
    
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    [data-testid="stHeader"] {
        background-color: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(10px);
    }
    
    [data-testid="stSidebar"] {
        background-color: #0b1120;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    :root {
        --kkb-orange: #FF5100;
        --kkb-blue: #1B2E49;
    }

    h1, h2, h3, h4, h5, h6 { color: white !important; font-weight: 600; }
    
    /* Widget Styling (Form Look) */
    .stRadio > div, .stMultiSelect > div, .stTextInput > div, .stTextArea > div {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Question Card */
    .question-card {
        background-color: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 5px solid var(--kkb-orange);
    }
    
    .evidence-box {
        font-size: 0.85rem;
        color: #94a3b8;
        background: rgba(0,0,0,0.2);
        padding: 10px;
        border-radius: 6px;
        margin-top: 10px;
    }
    
    .stButton button {
        background: rgba(255, 255, 255, 0.05);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background: var(--kkb-orange);
        border-color: var(--kkb-orange);
        color: white;
        font-weight: bold;
    }
    
    a { color: var(--kkb-orange) !important; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- LOGIC ---
def synthesize_strict_answer(question, data_result, doc_result, web_result=None):
    web_context = f"\nWEB CRAWLER SONUCU:\n{web_result}" if web_result else ""
    prompt = ChatPromptTemplate.from_template("""
    Sen profesyonel bir denetçisin. Soruya elindeki verilerle cevap ver.
    SORU: {question}
    VERİ: {data_output}
    DOKÜMAN: {doc_output}
    {web_context}
    Cevap:
    """)
    chain = prompt | llm_reasoning | StrOutputParser()
    return chain.invoke({"question": question, "data_output": data_result, "doc_output": doc_result, "web_context": web_context})

def solve_question_autofill_wrapper(ctx, question_obj, manual_urls, use_crawl, crawl_depth, crawl_limit):
    """
    Wrapper function that adds Streamlit context to worker threads.
    This prevents the 'missing ScriptRunContext' warning.
    """
    if ctx and add_script_run_ctx:
        add_script_run_ctx(ctx=ctx)
    
    return solve_question_autofill(question_obj, manual_urls, use_crawl, crawl_depth, crawl_limit)

def solve_question_autofill(question_obj, manual_urls=None, use_crawl=True, crawl_depth=2, crawl_limit=10):
    """Analyze a question and return suggested answer with timing information."""
    start_time = time.time()
    q_id = question_obj.get("questionId", "unknown")
    
    # Validate question structure
    if not validate_question_structure(question_obj):
        logger.error(f"Q{q_id}: Invalid question structure")
        return {
            "suggested_value": "",
            "selected_id": None,
            "selected_ids": [],
            "confidence_score": 0,
            "evidence_summary": "Geçersiz soru yapısı",
            "elapsed_time": 0
        }
    
    q_txt = question_obj.get("questionDescription", "")
    q_type = question_obj.get("questionType", "")
    q_opts = question_obj.get("answers", [])
    
    logger.info(f"Q{q_id}: Starting analysis - Type: {q_type}")
    
    # 1. Gather Context from Data Agent
    data_agent = get_data_agent()
    d_res = "Veri Yok"
    if data_agent:
        try:
            d_res = data_agent(q_txt).content
            logger.info(f"Q{q_id}: Data agent response length: {len(d_res)}")
        except Exception as e:
            logger.warning(f"Q{q_id}: Data agent error: {e}")
            d_res = "Veri Yok"
    
    # 2. Gather Context from Document Agent
    doc_agent = get_doc_agent()
    doc_res = "Doküman Yok"
    if doc_agent:
        try:
            doc_res = doc_agent.invoke({"messages": [HumanMessage(content=q_txt)]})["messages"][-1].content
            logger.info(f"Q{q_id}: Doc agent response length: {len(doc_res)}")
        except Exception as e:
            logger.warning(f"Q{q_id}: Doc agent error: {e}")
            doc_res = "Doküman Yok"

    # 3. Web Scraper (Smart Trigger)
    web_res = None
    if should_use_web_scraper(doc_res, d_res):
        if manual_urls:
            try:
                logger.info(f"Q{q_id}: Triggering web scraper")
                scraper = get_web_scraper_agent()
                web_res = scraper(q_txt, manual_urls=manual_urls, use_crawl=use_crawl, 
                                max_depth=crawl_depth, limit=crawl_limit)
                logger.info(f"Q{q_id}: Web scraper response length: {len(web_res) if web_res else 0}")
            except Exception as e:
                logger.error(f"Q{q_id}: Web scraper error: {e}")
                web_res = None

    # 4. AI Reasoning with Math Tool Support
    parser = JsonOutputParser()
    prompt = ChatPromptTemplate.from_template("""
    GÖREV: Aşağıdaki soruyu elindeki Rapor ve Web verilerine göre cevapla.
    
    SORU: {q_txt}
    TİP: {q_type}
    ŞIKLAR: {q_opts}
    
    ANALİZ VERİLERİ:
    - Excel/Data: {d_res}
    - Doküman: {doc_res}
    - Web: {web_res}
    
    ÖNEMLİ KURALLAR:
    1. MATEMATİKSEL İŞLEMLER: Eğer hesaplama gerekiyorsa (toplama, çarpma, birim dönüşümü), 
       hesaplama adımlarını açıkça göster. Örnek: "24 MWh × 1000 = 24,000 kWh"
    
    2. BİRİM DÖNÜŞÜMLERİ: Soru belirli bir birimde cevap istiyorsa (örn: kWh, kg, litre), 
       kaynaklarda farklı birimlerde veri varsa (MWh, ton, m³) mutlaka dönüştür ve hesaplamayı göster!
    
    3. DİL: Tüm çıktılar TÜRKÇE olmalıdır. İngilizce kelime veya cümle kullanma.
    
    4. KANITLAMA: Her cevap için kaynak, kanıt ve referans belirt.
    
    İSTENEN ÇIKTI (JSON):
    {{
      "suggested_value": "Bulduğun en doğru cevap (Metin, Sayı veya Seçenek)",
      "selected_id": "Eğer singleChoice ise eşleşen answerId (yoksa null)",
      "selected_ids": "Eğer multiChoice ise eşleşen answerId'lerin listesi (örn: [1, 3, 5])",
      "confidence_score": 0-100 arası sayı,
      "evidence": {{
        "answer": "Nihai cevap değeri. Örnek: '24,000 kWh' veya 'Evet, politika mevcut'",
        "proof": "DETAYLI TÜRKÇE AÇIKLAMA: Cevabın nasıl bulunduğunu, hesaplama varsa adım adım göster, hangi verilerin kullanıldığını açıkla. Minimum 2-3 cümle. Örnek: 'Sürdürülebilirlik Raporu'nda 2023 yılı için 24 MWh enerji tüketimi belirtilmiştir. Sorunun istediği birim kWh olduğu için dönüşüm yapıldı: 24 MWh × 1000 = 24,000 kWh. Bu değer şirketin toplam elektrik tüketimini göstermektedir.'",
        "reference": "Kaynak bilgisi: Dosya adı, Sayfa numarası, Tablo/Bölüm adı. Örnek: 'Kaynak: Sürdürülebilirlik Raporu 2023, Sayfa 34, Enerji Tüketimi Tablosu'"
      }}
    }}
    
    KANIT (evidence) YAPISI ÖRNEKLERİ:
    
    Örnek 1 - Matematiksel İşlem:
    {{
      "answer": "11,932,000 kg",
      "proof": "Kapsam 1 Emisyonlar tablosunda 2023 yılı için 11.932 tCO2e değeri bulunmaktadır. Sorunun istediği birim kg olduğu için dönüşüm yapıldı: 11.932 ton × 1000 = 11,932 kg. Bu değer doğrudan operasyonel faaliyetlerden kaynaklanan sera gazı emisyonlarını temsil etmektedir.",
      "reference": "Kaynak: Sürdürülebilirlik Raporu 2023, Sayfa 45, Kapsam 1 Emisyonlar Tablosu"
    }}
    
    Örnek 2 - Seçenekli Soru:
    {{
      "answer": "Evet",
      "proof": "Şirketin 2023 Sürdürülebilirlik Raporu'nun 'Çevre Politikaları' bölümünde detaylı bir çevre yönetim politikası açıklanmıştır. Politika, emisyon azaltma hedeflerini, enerji verimliliği önlemlerini ve atık yönetimi stratejilerini içermektedir.",
      "reference": "Kaynak: Sürdürülebilirlik Raporu 2023, Sayfa 12-15, Çevre Politikaları Bölümü"
    }}
    
    ÖNEMLİ: 
    - "answer" alanı kısa ve net olmalı (sadece cevap)
    - "proof" alanı detaylı açıklama ve hesaplamalar içermeli (2-3 cümle)
    - "reference" alanı tam kaynak bilgisi vermeli (dosya, sayfa, tablo)
    - Tüm alanlar TÜRKÇE olmalı
    """)
    
    try:
        chain = prompt | llm_reasoning | parser
        result = chain.invoke({
            "q_txt": q_txt, "q_type": q_type, "q_opts": q_opts,
            "d_res": d_res, "doc_res": doc_res, "web_res": web_res
        })
        
        # Validate AI response
        result = validate_ai_response(question_obj, result)
        
        # Apply unit conversion if needed
        if result.get("suggested_value"):
            result["suggested_value"] = validate_and_convert_answer(
                q_txt, 
                str(result["suggested_value"])
            )
        
        # Add elapsed time
        elapsed_time = time.time() - start_time
        result["elapsed_time"] = elapsed_time
        
        logger.info(f"Q{q_id}: Analysis complete - Confidence: {result.get('confidence_score')}%, Time: {elapsed_time:.2f}s")
        return result
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Q{q_id}: Analysis failed: {e}")
        return {
            "suggested_value": "",
            "selected_id": None,
            "selected_ids": [],
            "confidence_score": 0,
            "evidence_summary": f"Analiz hatası: {str(e)}",
            "elapsed_time": elapsed_time
        }

# --- INITIALIZATION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "target_urls" not in st.session_state: 
    st.session_state.target_urls = ["https://www.akbankinvestorrelations.com/tr/"]
if "form_data" not in st.session_state: st.session_state.form_data = {} # To store filled values
if "form_questions" not in st.session_state: st.session_state.form_questions = []
# Crawl settings
if "use_crawl" not in st.session_state: st.session_state.use_crawl = True
if "crawl_depth" not in st.session_state: st.session_state.crawl_depth = 2
if "crawl_limit" not in st.session_state: st.session_state.crawl_limit = 10

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 3rem; color: #FF5100;">🏢</div>
            <h2 style="color: white; margin: 0;">KKB</h2>
            <small style="color: #64748B; letter-spacing: 2px;">GREENDEKS</small>
        </div>
    """, unsafe_allow_html=True)
    
    st.caption("1. ADIM: KAYNAK YÜKLE")
    files = st.file_uploader("Rapor Yükle", accept_multiple_files=True, label_visibility="collapsed")
    if files:
        if st.button("Kaynağı İşle", type="primary"):
            with st.status("İndeksleniyor...", expanded=True) as s:
                path = os.path.join(os.getcwd(), "data", "inputs")
                os.makedirs(path, exist_ok=True)
                saved = []
                for f in files:
                    p = os.path.join(path, f.name)
                    with open(p, "wb") as w: w.write(f.getbuffer())
                    saved.append(p)
                ingest_files(saved)
                s.update(label="Hazır", state="complete")
    
    st.markdown("---")
    with st.expander("🌐 Web Tarama Ayarları"):
        u = st.text_input("URL Ekle")
        if st.button("Ekle"): 
            st.session_state.target_urls.append(u)
            st.success("Eklendi")
        
        st.markdown("**Tarama Modu:**")
        st.session_state.use_crawl = st.checkbox(
            "🕷️ Alt sayfaları da tara (Crawl Mode)",
            value=st.session_state.use_crawl,
            help="Aktif olduğunda, ana URL'deki tüm bağlantıları takip ederek alt sayfaları da tarar."
        )
        
        if st.session_state.use_crawl:
            st.session_state.crawl_depth = st.slider(
                "Tarama Derinliği",
                min_value=1,
                max_value=5,
                value=st.session_state.crawl_depth,
                help="Kaç seviye link takip edilecek (1 = sadece ana sayfadaki linkler)"
            )
            st.session_state.crawl_limit = st.slider(
                "Maksimum Sayfa Sayısı",
                min_value=5,
                max_value=50,
                value=st.session_state.crawl_limit,
                help="Taranacak maksimum sayfa sayısı"
            )

# --- MAIN ---
st.markdown("""
<div style="margin-bottom: 20px;">
    <h1 style="color: white; border-left: 5px solid #FF5100; padding-left: 15px;">KKB Greendeks AI</h1>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 Akıllı Form (Autofill)", "💬 Serbest Sohbet"])

# TAB 1: FORM ENGINE
with tab1:
    st.markdown("### 2. ADIM: SORU SETİ YÜKLE & DOLDUR")
    
    uploaded_json = st.file_uploader("Soru Seti JSON Dosyası", type="json")
    
    # Load JSON Logic
    if uploaded_json:
        data = json.load(uploaded_json)
        questions = data.get("questions", [])
        
        # Eğer yeni bir dosya ise state'i sıfırla veya güncelle
        if st.session_state.form_questions != questions:
            st.session_state.form_questions = questions
            st.session_state.form_data = {} # Reset answers

    # "ANALİZ ET" BUTONU
    if st.session_state.form_questions:
        if st.button("✨ Yapay Zeka ile Formu Doldur", type="primary"):
            logger.info(f"Starting autofill for {len(st.session_state.form_questions)} questions")
            prog_bar = st.progress(0, "Analiz Başlıyor...")
            
            # PARALLEL PROCESSING
            total_questions = len(st.session_state.form_questions)
            completed_count = 0
            
            # Get current Streamlit context to pass to threads
            ctx = get_script_run_ctx() if get_script_run_ctx else None
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=AppConfig.MAX_PARALLEL_WORKERS) as executor:
                # Submit all tasks with context
                future_to_qid = {
                    executor.submit(
                        solve_question_autofill_wrapper,
                        ctx,  # Pass context to wrapper
                        q,
                        st.session_state.target_urls,
                        st.session_state.use_crawl,
                        st.session_state.crawl_depth,
                        st.session_state.crawl_limit
                    ): q["questionId"]
                    for q in st.session_state.form_questions
                }


                
                # Process as they complete
                for future in concurrent.futures.as_completed(future_to_qid):
                    qid = future_to_qid[future]
                    try:
                        ai_res = future.result(timeout=AppConfig.AGENT_TIMEOUT_SECONDS)
                        # STATE'E KAYDET - Handle both old and new evidence formats
                        evidence_data = ai_res.get("evidence", ai_res.get("evidence_summary", {}))
                        st.session_state.form_data[qid] = {
                            "value": ai_res.get("suggested_value"),
                            "selected_id": ai_res.get("selected_id"),
                            "selected_ids": ai_res.get("selected_ids", []),
                            "confidence": ai_res.get("confidence_score"),
                            "evidence": evidence_data,  # Can be dict or string
                            "elapsed_time": ai_res.get("elapsed_time", 0)
                        }
                    except concurrent.futures.TimeoutError:
                        logger.error(f"Q{qid}: Timeout after {AppConfig.AGENT_TIMEOUT_SECONDS}s")
                        st.session_state.form_data[qid] = {
                            "value": "", "selected_id": None, "selected_ids": [],
                            "confidence": 0, 
                            "evidence": {"answer": "", "proof": "Zaman aşımı", "reference": ""}, 
                            "elapsed_time": AppConfig.AGENT_TIMEOUT_SECONDS
                        }
                    except Exception as e:
                        logger.error(f"Q{qid}: Processing error: {e}")
                        st.session_state.form_data[qid] = {
                            "value": "", "selected_id": None, "selected_ids": [],
                            "confidence": 0, 
                            "evidence": {"answer": "", "proof": f"Hata: {str(e)}", "reference": ""}, 
                            "elapsed_time": 0
                        }
                    
                    completed_count += 1
                    prog_bar.progress(completed_count / total_questions, f"Analiz ediliyor... ({completed_count}/{total_questions})")
            
            prog_bar.empty()
            
            # Calculate timing statistics
            all_times = [data.get("elapsed_time", 0) for data in st.session_state.form_data.values()]
            if all_times:
                total_time = sum(all_times)
                avg_time = total_time / len(all_times)
                max_time = max(all_times)
                min_time = min(all_times)
                
                # Format times
                total_str = f"{total_time:.1f}s" if total_time < 60 else f"{int(total_time//60)}m {int(total_time%60)}s"
                avg_str = f"{avg_time:.1f}s"
                max_str = f"{max_time:.1f}s"
                min_str = f"{min_time:.1f}s"
                
                st.success(f"""
                ✅ **Analiz Tamamlandı!**
                
                📊 **Performans İstatistikleri:**
                - Toplam Süre: {total_str}
                - Ortalama: {avg_str}/soru
                - En Hızlı: {min_str} | En Yavaş: {max_str}
                """)
            else:
                st.success("Analiz Tamamlandı! Lütfen cevapları kontrol ediniz.")


    # FORM RENDER (Google Forms Style)
    if st.session_state.form_questions:
        st.markdown("---")
        with st.form("audit_form"):
            for q in st.session_state.form_questions:
                qid = q["questionId"]
                label = f"{qid}. {q['questionDescription']}"
                qtype = q["questionType"]
                
                # Get current AI value
                ai_data = st.session_state.form_data.get(qid, {})
                current_val = ai_data.get("value", "")
                confidence = ai_data.get("confidence", 0)
                evidence = ai_data.get("evidence", "")
                sel_id = ai_data.get("selected_id", None)
                
                st.markdown(f'<div class="question-card">', unsafe_allow_html=True)
                st.markdown(f"**{label}**")
                
                # WIDGET SEÇİMİ
                if qtype == "singleChoice":
                    options = q.get("answers", [])
                    opt_labels = [o["answerDescription"] for o in options]
                    opt_ids = [o["answerId"] for o in options]
                    
                    # Index bul - Güvenli validasyon
                    idx = 0
                    
                    # Önce selected_id ile eşleştirmeyi dene
                    if sel_id is not None:
                        try:
                            # sel_id'nin opt_ids listesinde olup olmadığını kontrol et
                            if sel_id in opt_ids:
                                idx = opt_ids.index(sel_id)
                            else:
                                # sel_id bulunamadıysa, metin eşleştirmesi dene
                                if current_val:
                                    current_val_lower = str(current_val).lower().strip()
                                    for i, label in enumerate(opt_labels):
                                        if label.lower().strip() == current_val_lower:
                                            idx = i
                                            break
                        except (ValueError, IndexError, TypeError) as e:
                            print(f"Warning: Error matching option for question {qid}: {e}")
                            idx = 0
                    # Eğer sel_id yoksa ama current_val varsa, sadece metin eşleştirmesi yap
                    elif current_val:
                        try:
                            current_val_lower = str(current_val).lower().strip()
                            for i, label in enumerate(opt_labels):
                                if label.lower().strip() == current_val_lower:
                                    idx = i
                                    break
                        except (TypeError, AttributeError) as e:
                            print(f"Warning: Error matching text for question {qid}: {e}")
                            idx = 0
                    
                    # Son güvenlik kontrolü: Index sınırlarını kontrol et
                    if not (0 <= idx < len(opt_labels)):
                        print(f"Warning: Invalid index {idx} for question {qid} with {len(opt_labels)} options. Resetting to 0.")
                        idx = 0
                    
                    st.radio("Cevabınız:", opt_labels, index=idx, key=f"wdg_{qid}")
                
                elif qtype == "multiChoice":
                    options = q.get("answers", [])
                    opt_labels = [o["answerDescription"] for o in options]
                    opt_ids = [o["answerId"] for o in options]
                    
                    # Get AI-selected IDs and find matching labels - Güvenli validasyon
                    sel_ids = ai_data.get("selected_ids", [])
                    default_selections = []
                    
                    if sel_ids and isinstance(sel_ids, list):
                        for sel_id in sel_ids:
                            try:
                                if sel_id in opt_ids:
                                    idx = opt_ids.index(sel_id)
                                    # Index sınırlarını kontrol et
                                    if 0 <= idx < len(opt_labels):
                                        default_selections.append(opt_labels[idx])
                            except (ValueError, IndexError) as e:
                                # Geçersiz ID'leri atla
                                print(f"Warning: Invalid option ID {sel_id} for question {qid}: {e}")
                                continue
                    
                    st.multiselect("Seçimleriniz:", opt_labels, default=default_selections, key=f"wdg_{qid}")
                
                else: # openText, numeric
                    st.text_area("Yanıt:", value=str(current_val), key=f"wdg_{qid}")
                
                # AI KANIT KUTUSU
                if evidence:
                    elapsed = ai_data.get("elapsed_time", 0)
                    elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{int(elapsed//60)}m {int(elapsed%60)}s"
                    
                    # Confidence-based color coding
                    if int(confidence or 0) >= AppConfig.HIGH_CONFIDENCE_THRESHOLD:
                        color = "#4ade80"  # Green
                        icon = "✅"
                    elif int(confidence or 0) >= AppConfig.MEDIUM_CONFIDENCE_THRESHOLD:
                        color = "#fbbf24"  # Yellow
                        icon = "⚠️"
                    else:
                        color = "#f87171"  # Red
                        icon = "❌"
                    
                    # Format evidence - handle both structured (dict) and old (string) formats
                    if isinstance(evidence, dict):
                        # New structured format
                        answer_text = evidence.get("answer", "")
                        proof_text = evidence.get("proof", "")
                        reference_text = evidence.get("reference", "")
                        
                        evidence_html = f"""
                        <div class="evidence-box" style="border-left: 3px solid {color};">
                            <strong>{icon} AI Önerisi ({confidence}% Güven) • ⏱️ {elapsed_str}</strong><br><br>
                            <div style="margin-bottom: 8px;">
                                <strong style="color: #60a5fa;">📌 Cevap:</strong><br>
                                <span style="margin-left: 10px;">{answer_text}</span>
                            </div>
                            <div style="margin-bottom: 8px;">
                                <strong style="color: #a78bfa;">🔍 Kanıt:</strong><br>
                                <span style="margin-left: 10px;">{proof_text}</span>
                            </div>
                            <div>
                                <strong style="color: #fbbf24;">📚 Kaynak:</strong><br>
                                <span style="margin-left: 10px;">{reference_text}</span>
                            </div>
                        </div>
                        """
                    else:
                        # Old string format (backward compatibility)
                        evidence_html = f"""
                        <div class="evidence-box" style="border-left: 3px solid {color};">
                            <strong>{icon} AI Önerisi ({confidence}% Güven) • ⏱️ {elapsed_str}</strong><br>
                            {evidence}
                        </div>
                        """
                    
                    st.markdown(evidence_html, unsafe_allow_html=True)


                st.markdown('</div>', unsafe_allow_html=True)
            
            # SUBMIT
            submitted = st.form_submit_button("✅ Formu Onayla ve Kaydet")
            if submitted:
                logger.info("Form submitted by user")
                
                # Prepare export data
                export_data = {
                    "formId": data.get("formId", "unknown"),
                    "submittedAt": datetime.now().isoformat(),
                    "totalQuestions": len(st.session_state.form_questions),
                    "answers": []
                }
                
                for q in st.session_state.form_questions:
                    qid = q["questionId"]
                    widget_key = f"wdg_{qid}"
                    
                    # Get user's final answer from widget
                    user_answer = st.session_state.get(widget_key)
                    ai_suggestion = st.session_state.form_data.get(qid, {})
                    
                    export_data["answers"].append({
                        "questionId": qid,
                        "questionText": q["questionDescription"],
                        "questionType": q["questionType"],
                        "userAnswer": user_answer,
                        "aiSuggestion": {
                            "value": ai_suggestion.get("value"),
                            "confidence": ai_suggestion.get("confidence"),
                            "evidence": ai_suggestion.get("evidence"),
                            "processingTime": ai_suggestion.get("elapsed_time")
                        }
                    })
                
                # Store export data in session state
                st.session_state.export_data = export_data
                st.session_state.form_submitted = True
                
                st.balloons()
                st.success("✅ Form başarıyla kaydedildi! Aşağıdaki butona tıklayarak indirebilirsiniz.")
                logger.info(f"Form exported with {len(export_data['answers'])} answers")
        
        # Download button OUTSIDE the form
        if st.session_state.get("form_submitted", False) and "export_data" in st.session_state:
            json_str = json.dumps(st.session_state.export_data, ensure_ascii=False, indent=2)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            st.download_button(
                label="📥 Cevapları İndir (JSON)",
                data=json_str,
                file_name=f"form_answers_{timestamp}.json",
                mime="application/json",
                type="primary"
            )
    else:
        st.info("Lütfen sol taraftan veya yukarıdan bir Soru JSON dosyası yükleyin.")

# TAB 2: CHAT (Fallback)
with tab2:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg['role']=='user' else "🏢"):
            st.markdown(msg["content"])
    if prompt := st.chat_input("..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
