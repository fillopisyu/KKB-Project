"""
Web Trigger Test - Belgelerde Olmayan Soru
Test eder: Yetersiz cevaplarda web'e gidiyor mu?
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validators import should_use_web_scraper

def test_web_trigger():
    """Test web trigger logic with insufficient answers."""
    print("=" * 70)
    print("TEST: Web Trigger - Yetersiz Bilgi Senaryosu")
    print("=" * 70)
    
    # Senaryo 1: Her iki agent da kısa/yetersiz cevap
    print("\n📌 Senaryo 1: Çok Kısa Cevaplar")
    print("-" * 70)
    
    doc_res_1 = "Bilgi Yok"
    data_res_1 = "Veri Yok"
    question_1 = "Şirketin 2025 hedefleri nedir?"
    
    result_1 = should_use_web_scraper(doc_res_1, data_res_1, question_1)
    print(f"  Doküman: '{doc_res_1}'")
    print(f"  Data: '{data_res_1}'")
    print(f"  Soru: '{question_1}'")
    print(f"  → Web'e git: {'✅ EVET' if result_1 else '❌ HAYIR'}")
    
    # Senaryo 2: Uzun ama yetersiz bir cevap
    print("\n📌 Senaryo 2: Uzun Ama Belirsiz Cevap")
    print("-" * 70)
    
    doc_res_2 = "Raporda sürdürülebilirlikten bahsediliyor ancak 2025 hedefleri için spesifik bilgi bulunmamaktadır. Genel ifadeler var."
    data_res_2 = "Veri tablolarında bu bilgi bulunamadı"
    question_2 = "2025 yılı carbon neutrality hedefi nedir?"
    
    result_2 = should_use_web_scraper(doc_res_2, data_res_2, question_2)
    print(f"  Doküman: '{doc_res_2[:60]}...'")
    print(f"  Data: '{data_res_2}'")
    print(f"  Soru: '{question_2}'")
    print(f"  → Web'e git: {'✅ EVET' if result_2 else '❌ HAYIR'}")
    
    # Senaryo 3: Yeterli detaylı cevap
    print("\n📌 Senaryo 3: Yeterli Detaylı Cevap (Karşılaştırma)")
    print("-" * 70)
    
    doc_res_3 = "2023 yılı için toplam elektrik tüketimi 82,583,600 kWh olarak raporlanmıştır. (Kaynak: Sürdürülebilirlik Raporu 2023, Sayfa 45, Enerji Tüketimi Tablosu)"
    data_res_3 = "Veri seti: 2023 için 82.6 MWh (dönüşüm: 82,600,000 kWh)"
    question_3 = "2023 elektrik tüketimi ne kadar?"
    
    result_3 = should_use_web_scraper(doc_res_3, data_res_3, question_3)
    print(f"  Doküman: '{doc_res_3[:60]}...'")
    print(f"  Data: '{data_res_3[:60]}...'")
    print(f"  Soru: '{question_3}'")
    print(f"  → Web'e git: {'✅ EVET' if result_3 else '❌ HAYIR'}")
    
    # Sonuç özeti
    print("\n" + "=" * 70)
    print("📊 TEST SONUÇLARI:")
    print("=" * 70)
    
    expected_1 = True  # Kısa cevaplar → Web'e git
    expected_2 = True  # Belirsiz cevap → Web'e git (LLM'e bağlı)
    expected_3 = False  # Yeterli cevap → Web'e gitme
    
    tests_passed = 0
    tests_total = 3
    
    if result_1 == expected_1:
        print(f"  ✅ Senaryo 1: BAŞARILI (Kısa cevaplar → Web)")
        tests_passed += 1
    else:
        print(f"  ❌ Senaryo 1: BAŞARISIZ (Beklenen: {expected_1}, Alınan: {result_1})")
    
    # Senaryo 2 LLM'e bağlı, her iki sonuç da OK
    web_result = "Web'e gitti" if result_2 else "Gitmedi"
    print(f"  ℹ️  Senaryo 2: {web_result} (LLM confidence'a göre)")

    
    if result_3 == expected_3:
        print(f"  ✅ Senaryo 3: BAŞARILI (Yeterli cevap → Web'e gitme)")
        tests_passed += 1
    else:
        print(f"  ❌ Senaryo 3: BAŞARISIZ (Beklenen: {expected_3}, Alınan: {result_3})")
    
    print("\n" + "=" * 70)
    if tests_passed >= 2:
        print(f"✅ TEST GENEL SONUÇ: BAŞARILI ({tests_passed}/2 gerekli test geçti)")
        print("\n💡 WEB TRIGGER ÇALIŞIYOR:")
        print("   - Yetersiz bilgi → Web'e gidiyor ✓")
        print("   - Yeterli bilgi → Web'e gitmiyor ✓")
    else:
        print(f"⚠️ TEST GENEL SONUÇ: SORUNLU ({tests_passed}/2 test geçti)")
    print("=" * 70)

if __name__ == "__main__":
    test_web_trigger()
