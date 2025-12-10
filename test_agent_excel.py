import os
from ingestion.processor import ingest_excel_as_html  # Yeni fonksiyon
from agents.data_agent import get_data_agent

# Dosyayı bul
input_folder = os.path.join(os.getcwd(), "data", "inputs")
files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith('.xlsx')]

if files:
    # 1. Excel'i HTML'e çevir
    print("--- 1. EXCEL -> HTML DÖNÜŞÜMÜ ---")
    ingest_excel_as_html(files[0])

    # 2. Ajanı al
    print("\n--- 2. HTML AJANI OLUŞTURULUYOR ---")
    agent_runner = get_data_agent()

    # 3. Soruları sor
    sorular = [
        "2023 yılı Kapsam 1 emisyon değeri nedir?",
        "2023 yılı Engelli çalışan sayısı ve Toplam çalışan sayısı kaçtır? Oranı nedir?",
        "Elektrik tüketimi kaç GJ'dür? Bunu kWh'e çevirir misin?"
    ]

    print("\n--- 3. TEST BAŞLIYOR ---")
    for soru in sorular:
        print(f"\n❓ SORU: {soru}")
        try:
            # Bu sefer invoke değil direkt fonksiyonu çağırıyoruz (Chain yapısı)
            cevap = agent_runner(soru)
            print(f"🤖 CEVAP:\n{cevap.content}")
        except Exception as e:
            print(f"❌ Hata: {e}")
else:
    print("Dosya bulunamadı.")