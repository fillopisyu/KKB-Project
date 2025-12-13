from typing import Dict, Any, List
from core.logger import logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.config import llm_reasoning


def should_use_web_scraper(doc_res: str, data_res: str, question: str = "") -> bool:
    """
    LLM-based confidence evaluation: Should we search the web?
    
    Asks LLM to rate confidence (0-100) in current answers.
    If confidence is low, triggers web search.
    
    Args:
        doc_res: Response from document agent
        data_res: Response from data agent
        question: The original question (for context)
    
    Returns:
        True if web scraper should be used, False otherwise
    """
    # Hızlı kontrol: Eğer her iki agent da çok kısa cevap verdiyse
    if len(doc_res) < 20 and len(data_res) < 15:
        logger.info("Both agents returned very short responses - triggering web scraper")
        return True
    
    # Confidence threshold - bu değerin altındaysa web'e git
    CONFIDENCE_THRESHOLD = 60
    
    # LLM Confidence Evaluator Prompt
    prompt = ChatPromptTemplate.from_template("""
    Sen bir cevap kalite değerlendiricisisin. Görevin: Verilen soruya mevcut cevapların ne kadar güvenilir olduğunu değerlendirmek.
    
    SORU:
    {question}
    
    MEVCUT CEVAPLAR:
    
    [DOKÜMAN AGENT]:
    {doc_response}
    
    [VERİ AGENT]:
    {data_response}
    
    GÖREVİN:
    Yukarıdaki cevaplara 0-100 arası bir GÜVEN SKORU ver.
    
    GÜVEN SKORU KILAVUZU:
    
    90-100: ✅ YÜKSEK GÜVEN
    - Soruya tam, doğrudan ve net cevap var
    - Kaynak güvenilir (sayfa numarası, tablo referansı vs)
    - Yıl, birim, sayılar soruyla tam eşleşiyor
    - Çelişki yok
    
    60-89: ⚠️ ORTA GÜVEN
    - Cevap var ama tam değil veya kısmi
    - Kaynak referansı eksik
    - Yıl veya birim tam eşleşmiyor
    - Hafif belirsizlik var
    
    30-59: ⚠️ DÜŞÜK GÜVEN
    - Cevap çok genel veya alakalı ama spesifik değil
    - Kaynak zayıf
    - Eksik bilgi var
    - Belirsizlik yüksek
    
    0-29: ❌ ÇOK DÜŞÜK GÜVEN
    - Soruyla alakasız bilgi
    - Hiç cevap yok
    - Tamamen belirsiz
    
    CEVAP FORMATI (JSON):
    SADECE tek bir JSON objesi dön, array değil! confidence_score mutlaka SAYI olmalı (fifty, seksen gibi kelime KULLANMA!)
    
    {{
        "confidence_score": 75,
        "reason": "Kısa açıklama (Türkçe, neden bu skoru verdin?)"
    }}
    
    ÖNEMLİ: 
    - Array kullanma: [{{...}}] YANLIŞ
    - Tek obje kullan: {{...}} DOĞRU
    - confidence_score mutlaka sayı: 75 ✓, "seventy-five" ✗
    
    ÖRNEKLER:
    
    Örnek 1:
    Soru: "2023 elektrik tüketimi nedir?"
    Doküman: "2023 yılı için toplam 24,000 kWh elektrik tüketimi rapor edilmiştir. (Kaynak: Sürdürülebilirlik Raporu, Sayfa 34)"
    Skor: {{"confidence_score": 95, "reason": "Tam cevap, kaynak güvenilir, yıl ve birim eşleşiyor"}}
    
    Örnek 2:
    Soru: "2023 Kapsam 3 emisyonları nedir?"
    Doküman: "Kapsam 3 emisyonlardan bahsediliyor ancak 2023 için spesifik değer belirtilmemiş. 2022 yılı için 5,200 ton."
    Skor: {{"confidence_score": 35, "reason": "İlgili bilgi var ama istenilen yıl için veri yok"}}
    
    Örnek 3:
    Soru: "Şirketin çevre politikası var mı?"
    Doküman: "Sürdürülebilirlik bölümünde genel çevre taahhütlerinden bahsediliyor ancak resmi bir politika belgesi tespit edilemedi."
    Skor: {{"confidence_score": 45, "reason": "Kısmi bilgi var ama net cevap yok, belirsiz"}}
    """)
    
    try:
        parser = JsonOutputParser()
        chain = prompt | llm_reasoning | parser
        
        result = chain.invoke({
            "question": question or "Bilinmeyen soru",
            "doc_response": doc_res[:2000],  # İlk 2000 karakter
            "data_response": data_res[:2000]
        })
        
        confidence = result.get("confidence_score", 0)
        reason = result.get("reason", "No reason provided")
        
        # Web'e gitme kararı: Confidence threshold'dan düşükse
        needs_web = confidence < CONFIDENCE_THRESHOLD
        
        if needs_web:
            logger.info(
                f"LLM Confidence: {confidence}/100 (< {CONFIDENCE_THRESHOLD}) → "
                f"TRIGGER web scraper | Reason: {reason}"
            )
        else:
            logger.info(
                f"LLM Confidence: {confidence}/100 (>= {CONFIDENCE_THRESHOLD}) → "
                f"SKIP web scraper | Reason: {reason}"
            )
        
        return needs_web
        
    except Exception as e:
        # LLM evaluation başarısızsa, güvenli tarafta kal (web'e gitme)
        logger.error(f"Web trigger confidence evaluation error: {e}")
        return False


def validate_ai_response(question_obj: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate AI response matches question constraints and auto-fix common issues.
    
    Checks:
    - For singleChoice: selected_id exists in options
    - For multiChoice: all selected_ids exist in options
    - Auto-fixes by matching text when ID is invalid
    
    Args:
        question_obj: Question object with type and answers
        ai_result: AI-generated result with selected_id(s)
    
    Returns:
        Validated (and possibly corrected) ai_result
    """
    q_id = question_obj.get("questionId")
    q_type = question_obj.get("questionType")
    options = question_obj.get("answers", [])
    opt_ids = [o["answerId"] for o in options]
    opt_labels = [o["answerDescription"] for o in options]
    
    errors = []
    
    # Validate singleChoice
    if q_type == "singleChoice":
        sel_id = ai_result.get("selected_id")
        
        if sel_id is not None and sel_id not in opt_ids:
            errors.append(f"Invalid selected_id {sel_id}, valid IDs: {opt_ids}")
            
            # Auto-fix: try to match by text
            suggested_val = str(ai_result.get("suggested_value", "")).lower().strip()
            fixed = False
            
            for opt in options:
                if opt["answerDescription"].lower().strip() == suggested_val:
                    ai_result["selected_id"] = opt["answerId"]
                    logger.info(f"Q{q_id}: Auto-fixed selected_id from {sel_id} to {opt['answerId']} via text match")
                    fixed = True
                    break
            
            if not fixed:
                # Default to first option as last resort
                ai_result["selected_id"] = opt_ids[0] if opt_ids else None
                logger.warning(f"Q{q_id}: Could not match text, defaulting to first option")
    
    # Validate multiChoice
    elif q_type == "multiChoice":
        sel_ids = ai_result.get("selected_ids", [])
        
        if not isinstance(sel_ids, list):
            errors.append(f"selected_ids should be list, got {type(sel_ids)}")
            ai_result["selected_ids"] = []
        else:
            invalid_ids = [sid for sid in sel_ids if sid not in opt_ids]
            
            if invalid_ids:
                errors.append(f"Invalid IDs in selected_ids: {invalid_ids}")
                
                # Auto-fix: filter out invalid IDs
                valid_ids = [sid for sid in sel_ids if sid in opt_ids]
                ai_result["selected_ids"] = valid_ids
                logger.warning(f"Q{q_id}: Filtered out invalid IDs: {invalid_ids}")
    
    # Log all validation issues
    if errors:
        logger.warning(f"Q{q_id} validation issues: {'; '.join(errors)}")
    
    return ai_result


def validate_question_structure(question_obj: Dict[str, Any]) -> bool:
    """
    Validate that question object has required fields.
    
    Args:
        question_obj: Question object to validate
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["questionId", "questionDescription", "questionType"]
    
    for field in required_fields:
        if field not in question_obj:
            logger.error(f"Question missing required field: {field}")
            return False
    
    q_type = question_obj.get("questionType")
    valid_types = ["singleChoice", "multiChoice", "openText", "numeric"]
    
    if q_type not in valid_types:
        logger.error(f"Invalid question type: {q_type}")
        return False
    
    # Choice questions must have answers
    if q_type in ["singleChoice", "multiChoice"]:
        answers = question_obj.get("answers", [])
        if not answers:
            logger.error(f"Question {question_obj.get('questionId')} has no answers")
            return False
    
    return True


def safe_get_index(items: List[Any], target_id: Any, default: int = 0) -> int:
    """
    Safely get index of item in list, with bounds checking.
    
    Args:
        items: List to search
        target_id: Item to find
        default: Default index if not found or out of bounds
    
    Returns:
        Index of item or default
    """
    try:
        if target_id in items:
            idx = items.index(target_id)
            # Bounds check
            if 0 <= idx < len(items):
                return idx
    except (ValueError, TypeError) as e:
        logger.warning(f"Error finding index: {e}")
    
    return default
