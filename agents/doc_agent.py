import os
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
        """
    )

    return agent_app