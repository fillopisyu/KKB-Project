import streamlit as st
import os
import time
import json
import concurrent.futures
from langchain_core.messages import HumanMessage
from agents.data_agent import get_data_agent
from agents.doc_agent import get_doc_agent
from agents.web_scraper import get_web_scraper_agent
from agents.evaluator import evaluate_answer
from ingestion.processor import ingest_files
from core.config import llm_reasoning
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

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

def solve_question_autofill(question_obj, manual_urls=None):
    q_txt = question_obj.get("questionDescription", "")
    q_type = question_obj.get("questionType", "")
    q_opts = question_obj.get("answers", [])
    
    # 1. Gather Context
    data_agent = get_data_agent()
    d_res = "Veri Yok"
    if data_agent:
        try: d_res = data_agent(q_txt).content
        except: pass
    
    doc_agent = get_doc_agent()
    doc_res = "Doküman Yok"
    if doc_agent: 
        try: 
            from langchain_core.messages import HumanMessage
            doc_res = doc_agent.invoke({"messages": [HumanMessage(content=q_txt)]})["messages"][-1].content
        except: pass

    web_res = None
    if "bulunamadı" in doc_res.lower() or len(doc_res) < 50:
        if manual_urls:
            try:
                scraper = get_web_scraper_agent()
                web_res = scraper(q_txt, manual_urls=manual_urls)
            except: pass

    # 2. AI Reasoning
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
    
    ÖNEMLİ: Eğer soru belirli bir birimde cevap istiyorsa (örn: kWh, kg, litre), 
    kaynaklarda farklı birimlerde veri varsa (MWh, ton, m³) mutlaka dönüştür!
    
    İSTENEN ÇIKTI (JSON):
    {{
      "suggested_value": "Bulduğun en doğru cevap (Metin, Sayı veya Seçenek)",
      "selected_id": "Eğer singleChoice ise eşleşen answerId (yoksa null)",
      "selected_ids": "Eğer multiChoice ise eşleşen answerId'lerin listesi (örn: [1, 3, 5])",
      "confidence_score": 0-100 arası sayı,
      "evidence_summary": "Bu cevabı neden seçtiğine dair 1 cümlelik kanıt/kaynak."
    }}
    """)
    
    try:
        chain = prompt | llm_reasoning | parser
        return chain.invoke({
            "q_txt": q_txt, "q_type": q_type, "q_opts": q_opts,
            "d_res": d_res, "doc_res": doc_res, "web_res": web_res
        })
    except:
        return {"suggested_value": "", "selected_id": None, "confidence_score": 0, "evidence_summary": "Analiz hatası"}

# --- INITIALIZATION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "target_urls" not in st.session_state: 
    st.session_state.target_urls = ["https://www.akbankinvestorrelations.com/tr/"]
if "form_data" not in st.session_state: st.session_state.form_data = {} # To store filled values
if "form_questions" not in st.session_state: st.session_state.form_questions = []

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
    with st.expander("🌐 Web URL Ekle (Opsiyonel)"):
        u = st.text_input("URL")
        if st.button("Ekle"): 
            st.session_state.target_urls.append(u)
            st.success("Eklendi")

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
            prog_bar = st.progress(0, "Analiz Başlıyor...")
            # PARALLEL PROCESSING
            total_questions = len(st.session_state.form_questions)
            completed_count = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all tasks
                future_to_qid = {
                    executor.submit(solve_question_autofill, q, st.session_state.target_urls): q["questionId"] 
                    for q in st.session_state.form_questions
                }
                
                # Process as they complete
                for future in concurrent.futures.as_completed(future_to_qid):
                    qid = future_to_qid[future]
                    try:
                        ai_res = future.result()
                        # STATE'E KAYDET
                        st.session_state.form_data[qid] = {
                            "value": ai_res.get("suggested_value"),
                            "selected_id": ai_res.get("selected_id"),
                            "selected_ids": ai_res.get("selected_ids", []),
                            "confidence": ai_res.get("confidence_score"),
                            "evidence": ai_res.get("evidence_summary")
                        }
                    except Exception as e:
                        print(f"Error processing question {qid}: {e}")
                    
                    completed_count += 1
                    prog_bar.progress(completed_count / total_questions, f"Analiz ediliyor... ({completed_count}/{total_questions})")
            
            prog_bar.empty()
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
                    
                    # Index bul
                    idx = 0
                    if sel_id and sel_id in opt_ids:
                        idx = opt_ids.index(sel_id)
                    elif current_val: # sometimes AI returns text instead of ID
                         pass 
                    
                    st.radio("Cevabınız:", opt_labels, index=idx, key=f"wdg_{qid}")
                
                elif qtype == "multiChoice":
                    options = q.get("answers", [])
                    opt_labels = [o["answerDescription"] for o in options]
                    opt_ids = [o["answerId"] for o in options]
                    
                    # Get AI-selected IDs and find matching labels
                    sel_ids = ai_data.get("selected_ids", [])
                    default_selections = []
                    if sel_ids:
                        for sel_id in sel_ids:
                            if sel_id in opt_ids:
                                idx = opt_ids.index(sel_id)
                                default_selections.append(opt_labels[idx])
                    
                    st.multiselect("Seçimleriniz:", opt_labels, default=default_selections, key=f"wdg_{qid}")
                
                else: # openText, numeric
                    st.text_area("Yanıt:", value=str(current_val), key=f"wdg_{qid}")
                
                # AI KANIT KUTUSU
                if evidence:
                    color = "#4ade80" if int(confidence or 0) > 70 else "#f87171"
                    st.markdown(f"""
                    <div class="evidence-box" style="border-left: 3px solid {color};">
                        <strong>🤖 AI Önerisi ({confidence}% Güven):</strong><br>
                        {evidence}
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)
            
            # SUBMIT
            submitted = st.form_submit_button("✅ Formu Onayla ve Kaydet")
            if submitted:
                st.balloons()
                st.success("Form başarıyla kaydedildi! (Export işlemi burada yapılabilir)")
                # JSON Export logic could go here
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
