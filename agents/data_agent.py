import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from core.config import llm_reasoning
from ingestion.processor import STRUCTURED_STORE


@st.cache_resource
def get_data_agent():
    """
    Excel/CSV verilerini HTML formatında analiz eden ajan.
    (Genel kültürü kapatılmış, sadece veriye odaklı versiyon)
    """
    if not STRUCTURED_STORE:
        return None

    file_name = list(STRUCTURED_STORE.keys())[0]
    tables = STRUCTURED_STORE[file_name]
    full_context = "\n\n".join(tables)

    print(f"🌐 Veri Analisti Hazırlandı ({len(tables)} tablo)")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Sen sadece veri okuyan bir robotsun. Genel kültürün, yemek tarifi bilgin veya dünya bilgin YOKTUR.
        Sadece sana verilen HTML tablosunu okuyabilirsin.

        GÖREVİN:
        Kullanıcının sorusunu AŞAĞIDAKİ HTML TABLOLARI içinde ara.

        KESİN VE AŞILAMAZ KURALLAR:
        1. **ASLA UYDURMA:** Eğer cevap tabloda yoksa, sadece "Veri tablolarında bu bilgi bulunamadı" de. Asla dışarıdan bilgi (tarif, tarih, genel bilgi) ekleme.
        2. **SAYILAR:** Sadece tablodaki sayıları kullan.
        3. **BAĞLAM DIŞI:** Eğer kullanıcı "Fasülye tarifi", "Hava durumu" gibi alakasız bir şey sorarsa, "Bu bilgi veri setinde mevcut değil" de.
        4. **BİRİM DÖNÜŞÜMLERİ:** Eğer soru belirli bir birimde cevap istiyorsa (örn: kWh), tabloda farklı birimlerde (MWh, GWh) veri varsa mutlaka dönüştür. Örnek:
           - Enerji: 1 MWh = 1,000 kWh | 1 GWh = 1,000,000 kWh
           - Emisyon: 1 ton = 1,000 kg | 1 kton = 1,000 ton
           - Su: 1 m³ = 1,000 litre

        VERİLER (HTML FORMATINDA):
        {html_context}
        """),
        ("user", "{input}")
    ])

    chain = prompt | llm_reasoning

    def run_agent(question):
        return chain.invoke({
            "html_context": full_context,
            "input": question
        })

    return run_agent