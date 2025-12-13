"""
Test script: Page number reference verification
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.doc_agent import get_doc_agent
from langchain_core.messages import HumanMessage

def test_page_numbers():
    """Test if doc agent includes page numbers in responses."""
    print("=" * 60)
    print("TEST: Page Number References in Doc Agent")
    print("=" * 60)
    
    # Get doc agent
    agent = get_doc_agent()
    
    if not agent:
        print("❌ Doc agent not available")
        return
    
    # Test question
    test_question = "2023 yılı elektrik tüketimi nedir?"
    
    print(f"\n📋 Test Sorusu: {test_question}")
    print("\n🔍 Doc Agent'ı çağırıyorum...")
    
    try:
        # Call agent
        result = agent.invoke({"messages": [HumanMessage(content=test_question)]})
        response = result["messages"][-1].content
        
        print("\n📄 Doc Agent Cevabı:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
        # Check for page numbers
        has_page_bracket = "[Sayfa" in response or "[sayfa" in response
        has_page_paren = "(Sayfa" in response or "(sayfa" in response
        has_page_keyword = "Sayfa" in response or "sayfa" in response
        
        print("\n🔎 Sayfa Numarası Kontrolü:")
        print(f"   [Sayfa X] formatı: {'✅ VAR' if has_page_bracket else '❌ YOK'}")
        print(f"   (Sayfa X) formatı: {'✅ VAR' if has_page_paren else '❌ YOK'}")
        print(f"   'Sayfa' kelimesi: {'✅ VAR' if has_page_keyword else '❌ YOK'}")
        
        # Check for source
        has_source = "Kaynak:" in response or "kaynak:" in response
        print(f"   Kaynak referansı: {'✅ VAR' if has_source else '❌ YOK'}")
        
        print("\n" + "=" * 60)
        if has_page_keyword and has_source:
            print("✅ TEST BAŞARILI: Sayfa numarası ve kaynak var!")
        else:
            print("⚠️ TEST UYARI: Sayfa numarası veya kaynak eksik!")
            print("\n💡 Olası sebepler:")
            print("   1. PDF'de sayfa metadata'sı eksik olabilir")
            print("   2. Agent prompt'u sayfa numarasını kullanmıyor olabilir")
            print("   3. Retriever sayfa bilgisini döndürmüyor olabilir")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ HATA: {e}")

if __name__ == "__main__":
    test_page_numbers()
