from typing import Dict, Any, List
from core.logger import logger


def should_use_web_scraper(doc_res: str, data_res: str) -> bool:
    """
    Determine if web scraping is needed based on agent responses.
    
    More robust than checking just for "bulunamadı" - checks multiple
    keywords and response lengths from both data and document agents.
    
    Args:
        doc_res: Response from document agent
        data_res: Response from data agent
    
    Returns:
        True if web scraper should be used, False otherwise
    """
    # Keywords indicating no information found
    no_info_keywords = [
        "bulunamadı", 
        "bilgi yok", 
        "mevcut değil",
        "bulunmamaktadır", 
        "tespit edilemedi",
        "bilgi bulunamadı",
        "veri yok",
        "dokümanlarda yok"
    ]
    
    # Check document response
    doc_has_info = (
        len(doc_res) > 50 and 
        not any(kw in doc_res.lower() for kw in no_info_keywords)
    )
    
    # Check data response
    data_has_info = (
        len(data_res) > 20 and 
        not any(kw in data_res.lower() for kw in no_info_keywords)
    )
    
    # Use web scraper if BOTH sources are insufficient
    should_scrape = not (doc_has_info or data_has_info)
    
    if should_scrape:
        logger.info(f"Web scraper triggered - Doc length: {len(doc_res)}, Data length: {len(data_res)}")
    
    return should_scrape


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
