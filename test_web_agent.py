import os
import sys
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Kendi modüllerimiz
try:
    from ingestion.processor import ingest_files, URL_STORE
    from agents.web_scraper import get_web_scraper_agent
except ImportError as e:
    print(f"❌ Kritik Import Hatası: {e}")
    print("Lütfen projenin ana dizininde olduğunuzdan emin olun.")
    sys.exit(1)


def setup_test_data():
    """Test için gerekli klasör ve dosyayı oluşturur."""
    input_folder = os.path.join(os.getcwd(), "data", "inputs")
    os.makedirs(input_folder, exist_ok=True)

    urls_file = os.path.join(input_folder, "urls.txt")

    # Eğer urls.txt yoksa veya içi boşsa örnek bir link ekleyelim
    if not os.path.exists(urls_file) or os.stat(urls_file).st_size == 0:
        print("📝 urls.txt oluşturuluyor...")
        with open(urls_file, "w", encoding="utf-8") as f:
            # Örnek olarak Akbank Sürdürülebilirlik sayfasını ekliyoruz
            f.write("https://www.akbank.com/tr-tr/akbank-hakkinda/surdurulebilirlik/Sayfalar/default.aspx")

    return urls_file


def test_web_agent():
    print("\n🧪 --- WEB AJANI ENTEGRASYON TESTİ BAŞLIYOR --- 🧪\n")

    # 1. Hazırlık
    print("1️⃣ Dosya Kontrolü...")
    urls_file_path = setup_test_data()
    print(f"   ✅ Hedef Dosya: {urls_file_path}")

    # 2. Ingestion (Veri İşleme)
    print("\n2️⃣ Veri Yükleme (Ingestion) Çalışıyor...")
    # Bu işlem urls.txt'yi okuyup URL_STORE listesine (RAM'e) atmalı
    ingest_files([urls_file_path])

    # 3. Hafıza Kontrolü
    print("\n3️⃣ Hafıza Kontrolü (URL_STORE)...")
    if not URL_STORE:
        print("❌ HATA: URL_STORE hala boş! 'ingestion/processor.py' içindeki 'extend' düzeltmesi yapılmamış olabilir.")
        return
    else:
        print(f"   ✅ Hafızadaki Link Sayısı: {len(URL_STORE)}")
        print(f"   🔗 Linkler: {URL_STORE}")

    # 4. Ajanı Başlatma
    print("\n4️⃣ Web Ajanı (Scraper) Hazırlanıyor...")
    try:
        scraper_agent = get_web_scraper_agent()
    except Exception as e:
        print(f"❌ Ajan Oluşturma Hatası: {e}")
        return

    # 5. Soru Sorma
    print("\n5️⃣ Soru Soruluyor...")
    soru = "Akbank'ın sürdürülebilirlik stratejisinin ana odak noktaları nelerdir?"
    print(f"   ❓ Soru: {soru}")
    print("   ⏳ Firecrawl siteye gidiyor, lütfen bekleyin...\n")

    try:
        # Ajanı parametresiz çağırıyoruz, otomatik olarak URL_STORE'u kullanacak
        cevap = scraper_agent(soru)

        print("=" * 60)
        print("🤖 WEB AJANI CEVABI:")
        print("=" * 60)
        print(cevap)
        print("=" * 60)

        if "Hata" not in cevap and "Bulunamadı" not in cevap:
            print("\n✅ TEST BAŞARILI! Sistem uçtan uca çalışıyor.")
        else:
            print("\n⚠️ TEST UYARISI: Cevap döndü ama hata veya yetersiz bilgi içeriyor olabilir.")

    except Exception as e:
        print(f"❌ Çalıştırma Hatası: {e}")


if __name__ == "__main__":
    test_web_agent()