import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.tools import Tool

# --- YENİ SÜRÜM (v1) DEĞİŞİKLİĞİ ---
# Artık AgentExecutor yok. Doğrudan create_agent kullanıyoruz.
from langchain.agents import create_agent
# -----------------------------------

from core.config import llm_reasoning, embedding_model, VECTOR_DB_PATH


# --- MANUEL TOOL WRAPPER ---
def create_retriever_tool_manual(retriever, name, description):
    def retrieve_docs(query: str):
        docs = retriever.invoke(query)
        if not docs:
            return "Dokümanlarda ilgili bilgi bulunamadı."
        return "\n\n".join([doc.page_content for doc in docs])

    return Tool(
        name=name,
        func=retrieve_docs,
        description=description
    )


@st.cache_resource
def get_doc_agent():
    """
    LangChain v1 uyumlu Doküman Ajanı.
    """

    # 1. Vektör DB Kontrolü
    if not os.path.exists(VECTOR_DB_PATH):
        print("⚠️ Uyarı: Vektör veritabanı bulunamadı.")
        return None

    # 2. Bağlantı
    vector_db = Chroma(
        persist_directory=VECTOR_DB_PATH,
        embedding_function=embedding_model
    )
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

    # 3. Tool Hazırlığı
    retriever_tool = create_retriever_tool_manual(
        retriever,
        name="search_reports",
        description="Şirket raporlarında arama yap."
    )
    tools = [retriever_tool]

    # 4. Ajanı Oluştur (TEK ADIM - MODERN YÖNTEM)
    # create_agent fonksiyonu, arka planda graph yapısını kurar ve çalışmaya hazır bir 'app' döndürür.
    print("🤖 Doküman Ajanı (v1 Modern) hazırlanıyor...")

    agent_app = create_agent(
        model=llm_reasoning,
        tools=tools,
        system_prompt="""
        Sen uzman bir Sürdürülebilirlik Denetçisisin.
        Görevin: 'search_reports' aracını kullanarak sorulara dokümanlardan yanıt bulmak.

        KURALLAR:
        1. Asla uydurma, mutlaka dokümanda ara.
        2. Her bilginin yanına (Kaynak: Faaliyet Raporu) gibi not düş.
        3. Bilgi yoksa "Dokümanlarda bulunamadı" de.
        
        BİRİM DÖNÜŞÜMLERİ:
        4. Eğer soru belirli bir birimde (örn: kWh) cevap istiyorsa, dokümanda farklı birimlerde (MWh, GWh) veri olabilir.
        5. Mutlaka birim dönüşümü yap ve doğru sonucu ver.
        
        Önemli Dönüşümler:
        - Enerji: 1 MWh = 1,000 kWh | 1 GWh = 1,000,000 kWh
        - Emisyon: 1 ton = 1,000 kg | 1 kton = 1,000 ton
        - Su: 1 m³ = 1,000 litre
        
        Örnek: Soru "kWh cinsinden elektrik tüketimi" soruyor ama dokümanda "150 MWh" yazıyorsa, 
        cevabın "150,000 kWh" olmalı.
        """
    )

    return agent_app