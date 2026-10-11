import logging
from typing import Dict, Any
from app.orchestrator.state import AnalysisState
from app.services.multilingual import detect_language, translate_to_english
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

async def detect_and_extract(state: AnalysisState) -> Dict[str, Any]:
    """
    Node 1: Language detection, technical translation (if Indic), and structured requirement extraction.
    """
    input_text = state.get("input_text", "")
    req_lang = state.get("input_language", "auto")

    # Detect language
    detected_lang = req_lang if req_lang != "auto" else detect_language(input_text)
    
    # Translate if necessary
    processed_text, was_translated = await translate_to_english(input_text, detected_lang)

    # Extract structured technical requirements
    extracted = await llm_service.extract_requirements_llm(processed_text)
    
    return {
        "processed_text": processed_text,
        "detected_language": detected_lang,
        "was_translated": was_translated,
        "product_identity": extracted.get("product_identity", "General Procurement Item"),
        "application": extracted.get("application", "General Works"),
        "mentioned_standards": extracted.get("mentioned_standards", []),
        "extracted_requirements": extracted.get("requirements", []),
        "requery_count": 0,
        "needs_requery": False
    }
