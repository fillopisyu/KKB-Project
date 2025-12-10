from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from core.config import llm_reasoning


# Çıktı formatını garantiye almak için Pydantic modeli
class EvaluationOutput(BaseModel):
    status: str = Field(description="'YETERLİ', 'YETERSİZ' veya 'ALAKASIZ'")
    reason: str = Field(description="Neden bu kararın verildiğinin detaylı açıklaması")
    score: int = Field(description="0-100 arası güven skoru")


def evaluate_answer(question, answer, context):
    """
    Üretilen cevabı 'Konu Alakası', 'Doğruluk' ve 'Kanıt' açısından sıkı denetler.
    """
    print("\n⚖️ Denetçi (Evaluator) Kontrol Ediyor...")

    parser = JsonOutputParser(pydantic_object=EvaluationOutput)

    prompt = ChatPromptTemplate.from_template("""
    Sen son derece titiz ve acımasız bir "ESG (Çevresel, Sosyal, Yönetişim) Başdenetçisisin".
    Görevin, yapay zekanın ürettiği cevabı aşağıdaki katı kurallara göre puanlamaktır.

    SORU: {question}

    ÜRETİLEN CEVAP:
    {answer}

    KULLANILAN BAĞLAM (HAM VERİ):
    {context}

    --- PUANLAMA CETVELİ (RUBRIC) ---

    1. **KONU DIŞI / ALAKASIZ SORULAR (0 - 20 PUAN):**
       - Soru; yemek tarifi, spor, genel kültür, sohbet veya şirketin raporlarıyla ilgisi olmayan bir konuysa.
       - Cevap ne kadar düzgün olursa olsun, konu dışıysa SKOR DÜŞÜK OLMALIDIR.
       - Durum: "ALAKASIZ"

    2. **BİLGİ BULUNAMADI (30 - 50 PUAN):**
       - Soru konuyla ilgili (Örn: Emisyon) ama dokümanlarda veri yoksa.
       - Sistem "Bilgi bulunamadı" dediyse bu dürüst bir cevaptır ama kullanıcı tatmin olmadığı için skor orta seviyede kalmalıdır.
       - Durum: "YETERSİZ"

    3. **BİLGİ VAR AMA KANIT EKSİK (51 - 80 PUAN):**
       - Cevap doğru görünüyor ama "Sayfa No", "Tablo Adı" veya net bir kaynak gösterilmemiş.
       - Durum: "YETERSİZ"

    4. **MÜKEMMEL (85 - 100 PUAN):**
       - Soru ESG ile ilgili.
       - Cevap net ve sayısal (gerekirse).
       - KANIT METNİ ve KAYNAK (Sayfa No/Tablo) kesinlikle mevcut.
       - Durum: "YETERLİ"

    GÖREVİN:
    Yukarıdaki cetvele göre cevabı analiz et. "Kuru fasülye" gibi saçma sorulara asla yüksek puan verme.

    ÇIKTI FORMATI (JSON):
    {{
        "status": "YETERLİ" | "YETERSİZ" | "ALAKASIZ",
        "reason": "Kısa ve net açıklama.",
        "score": <0-100 arası tamsayı>
    }}
    """)

    chain = prompt | llm_reasoning | parser

    try:
        result = chain.invoke({
            "question": question,
            "answer": answer,
            "context": context
        })
        return result
    except Exception as e:
        return {"status": "HATA", "reason": str(e), "score": 0}