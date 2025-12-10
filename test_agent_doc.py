import os
from ingestion.processor import ingest_files
from agents.doc_agent import get_doc_agent
from langchain_core.messages import HumanMessage

# Veri klasörü
input_folder = os.path.join(os.getcwd(), "data", "inputs")
files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith('.pdf')]

if files:
    print("--- 1. YÜKLEME KONTROLÜ ---")
    # Zaten yüklendiği için tekrar ingest etmeye gerek yok ama
    # yeni dosya eklenirse diye çağırabiliriz.
    # ingest_files(files)
    print("✅ Vektör veritabanı zaten hazır kabul ediliyor.")

    print("\n--- 2. DOKÜMAN AJANI (v1) HAZIRLANIYOR ---")
    doc_agent = get_doc_agent()

    if doc_agent:
        # TEST SORULARI
        sorular = [
            "Şirketin İnsan Hakları politikası var mı?",
            "Atık yönetimi ve geri dönüşüm konusunda neler yapılıyor?",
            "Yönetim Kurulunda kadın üye oranı hakkında bir hedef var mı?"
        ]

        print("\n--- 3. AJAN TEST BAŞLIYOR ---")
        for soru_metni in sorular:
            print(f"\n❓ SORU: {soru_metni}")
            try:
                # --- MODERN YÖNTEM (v1) ---
                # Girdi: Mesaj listesi
                # Çıktı: Güncellenmiş mesaj listesi (En son mesaj cevaptır)

                response = doc_agent.invoke({"messages": [HumanMessage(content=soru_metni)]})

                # Son mesajı al (Yapay zekanın cevabı)
                son_cevap = response["messages"][-1].content

                print(f"🤖 CEVAP:\n{son_cevap}")

            except Exception as e:
                print(f"❌ Hata Detayı: {e}")
                import traceback

                traceback.print_exc()

else:
    print("⚠️ data/inputs klasörüne PDF dosyasını eklemeyi unutmayın!")