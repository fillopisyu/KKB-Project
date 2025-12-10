import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

# Modüllerimiz
from agents.data_agent import get_data_agent
from agents.doc_agent import get_doc_agent
from agents.evaluator import evaluate_answer  # <-- YENİ EKLENDİ
from ingestion.processor import ingest_files
from core.config import llm_reasoning


# --- GELİŞMİŞ SENTEZLEYİCİ ---
def synthesize_strict_answer(question, data_result, doc_result):
    """
    Rehber dokümana uygun olarak 'Cevap', 'Kanıt' ve 'Kaynak' formatında çıktı üretir.
    """
    print("\n🧠 Sentezleyici Yanıtı Formatlıyor...")

    prompt = ChatPromptTemplate.from_template("""
    Sen "Greendeks" projesi için çalışan bir veri giriş asistanısın.
    Kullanıcının sorusuna, elindeki Veri ve Doküman analizlerine dayanarak cevap vermelisin.

    SORU: {question}

    ANALİZ 1 (EXCEL VERİSİ):
    {data_output}

    ANALİZ 2 (PDF DOKÜMANI):
    {doc_output}

    GÖREVİN:
    Bu bilgileri birleştir ve aşağıdaki formatta KESİN bir çıktı ver.
    Eğer seçenekli bir soruysa (Evet/Hayır gibi), rehber dokümana uygun şıkkı seç.

    İSTENEN FORMAT:
    --------------------------------------------------
    DOĞRU CEVAP: [Sorunun net cevabı. Örn: 11.932 tCO2e veya Evet, politika var]
    KANIT METNİ: [Rapordan veya tablodan alınan, cevabı destekleyen 1-2 cümlelik alıntı veya veri satırı]
    KAYNAK: [Dosya adı ve Sayfa Numarası / Tablo Adı]
    --------------------------------------------------

    Lütfen yorum yapma, sadece bu formatı doldur.
    """)

    chain = prompt | llm_reasoning | StrOutputParser()

    return chain.invoke({
        "question": question,
        "data_output": data_result,
        "doc_output": doc_result
    })


# --- ANA UYGULAMA ---
def main():
    print("🚀 Greendeks Denetçi Asistanı Başlatılıyor...")

    # 1. Dosya Yükleme
    input_folder = os.path.join(os.getcwd(), "data", "inputs")
    if not os.path.exists(input_folder):
        print("❌ HATA: 'data/inputs' klasörü yok!")
        return

    ingest_files([os.path.join(input_folder, f) for f in os.listdir(input_folder)])

    # 2. Ajanları Başlat
    data_agent = get_data_agent()
    doc_agent = get_doc_agent()

    print("\n✅ SİSTEM HAZIR! (Çıkış için 'q')")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n👤 SORU: ")
            if user_input.lower() in ['q', 'exit']: break

            print("-" * 30)

            # --- ADIM 1: VERİ TOPLAMA (PARALEL) ---
            # Excel Ajanı
            data_res = "Veri bulunamadı."
            if data_agent:
                print("📊 Excel taranıyor...")
                try:
                    raw_res = data_agent(user_input)
                    data_res = raw_res.content if hasattr(raw_res, 'content') else str(raw_res)
                except:
                    pass

            # PDF Ajanı
            doc_res = "Doküman bulunamadı."
            if doc_agent:
                print("📄 Raporlar okunuyor...")
                try:
                    raw_res = doc_agent.invoke({"messages": [HumanMessage(content=user_input)]})
                    doc_res = raw_res["messages"][-1].content
                except:
                    pass

            # --- ADIM 2: SENTEZ (FORMATLAMA) ---
            formatted_answer = synthesize_strict_answer(user_input, data_res, doc_res)

            # --- ADIM 3: DENETİM (EVALUATION) ---
            # Sentezlenen cevabı denetçiye gönderiyoruz
            audit_result = evaluate_answer(
                question=user_input,
                answer=formatted_answer,
                context=f"Excel: {data_res}\nPDF: {doc_res}"
            )

            # --- SONUÇ EKRANI ---
            print("\n" + "=" * 60)
            print(formatted_answer)  # Cevabı Bas
            print("=" * 60)

            # Denetim Raporu
            if audit_result['status'] == 'YETERLİ':
                print(f"✅ DENETİM GEÇTİ (Güven Skoru: {audit_result['score']}/100)")
            else:
                print(f"⚠️ DENETİM UYARISI: {audit_result['status']}")
                print(f"   Sebep: {audit_result['reason']}")
                print(f"   Güven Skoru: {audit_result['score']}/100")

        except Exception as e:
            print(f"❌ Hata: {e}")


if __name__ == "__main__":
    main()