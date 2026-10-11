import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._init_client()

    def _init_client(self):
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Google GenAI client initialized successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client: {e}")
                self._client = None
        else:
            self._client = None

    def is_available(self) -> bool:
        return self._client is not None or bool(os.getenv("GEMINI_API_KEY"))

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if self._client is None and settings.GEMINI_API_KEY:
            self._init_client()

        if self._client is not None:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction if system_instruction else None,
                    temperature=0.2,
                )
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}")
        
        # Fallback response
        return ""

    async def extract_requirements_llm(self, input_text: str) -> Dict[str, Any]:
        """
        Extracts structured parameters, product identity, and mentioned standards.
        Returns JSON format.
        """
        system_instruction = (
            "You are an expert technical auditor and Indian Standards analyst for government procurement.\n"
            "Analyze the technical specification or tender description. Extract:\n"
            "1. product_identity: Primary product name (e.g. 'Ordinary Portland Cement 43 Grade', 'TMT Steel Bars')\n"
            "2. application: Specific use case (e.g. 'Reinforced concrete construction in coastal environment')\n"
            "3. mentioned_standards: Any IS numbers cited in text (e.g. ['IS 269:2015', 'IS 456'])\n"
            "4. requirements: Array of structured technical requirements with {category, parameter, operator, value, unit}\n"
            "Respond strictly in JSON format."
        )

        prompt = f"Extract all technical parameters and mentioned standards from this specification:\n\n{input_text}"

        if self._client is not None:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=config
                )
                return json.loads(response.text)
            except Exception as e:
                logger.warning(f"Gemini extraction failed, using deterministic regex extractor: {e}")

        # Deterministic Regex & Pattern-based Fallback Extractor
        return self._deterministic_extract(input_text)

    def _deterministic_extract(self, text: str) -> Dict[str, Any]:
        """Regex and rule-based extraction fallback for deterministic offline execution."""
        # Find mentioned IS standards
        is_pattern = r'\bIS\s*:?\s*(\d{2,5}(?:\s*(?:Part|Pt|\(Part\))\s*\d+)?(?:\s*:\s*\d{4})?)\b'
        matches = re.findall(is_pattern, text, re.IGNORECASE)
        mentioned_standards = [f"IS {m.strip()}" for m in matches]

        # Identify product keywords
        lower = text.lower()
        product_identity = "General Procurement Item"
        application = "Government Procurement & Works"

        if "cement" in lower or "opc" in lower or "ppc" in lower:
            product_identity = "Portland Cement"
            application = "Concrete Construction"
        elif "steel" in lower or "tmt" in lower or "rebar" in lower or "fe 500" in lower:
            product_identity = "High Strength Deformed Steel Bars"
            application = "Reinforced Concrete Structures"
        elif "cable" in lower or "wire" in lower or "conductor" in lower:
            product_identity = "PVC Insulated Electrical Cables"
            application = "Electrical Wiring & Distribution"
        elif "water" in lower and ("drink" in lower or "potable" in lower or "test" in lower):
            product_identity = "Drinking / Potable Water"
            application = "Public Health & Quality Testing"
        elif "pipe" in lower:
            product_identity = "Pipes & Fittings"
            application = "Plumbing / Water Supply"

        # Extract numeric requirements
        requirements = []
        # Match pattern: <Parameter Name> <Operator> <Number> <Unit>
        param_patterns = [
            (r'compressive\s+strength\s*(?:>=|>|is|of)?\s*(\d+(?:\.\d+)?)\s*(mpa|n/mm2|kg/cm2)', "mechanical", "Compressive Strength"),
            (r'tensile\s+strength\s*(?:>=|>|is|of)?\s*(\d+(?:\.\d+)?)\s*(mpa|n/mm2)', "mechanical", "Tensile Strength"),
            (r'yield\s+(?:stress|strength)\s*(?:>=|>|is|of)?\s*(\d+(?:\.\d+)?)\s*(mpa|n/mm2)', "mechanical", "Yield Stress"),
            (r'thickness\s*(?:>=|>|is|of)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|micron)', "physical", "Thickness"),
            (r'diameter\s*(?:>=|>|is|of)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|inch)', "physical", "Diameter"),
            (r'voltage\s*(?:grade|rating)?\s*(?:is|of)?\s*(\d+)\s*(v|kv|volts)', "electrical", "Voltage Grade"),
            (r'fineness\s*(?:>=|>|is|of)?\s*(\d+(?:\.\d+)?)\s*(m2/kg|sq\.m/kg)', "physical", "Fineness"),
            (r'carbon\s*(?:content|%)?\s*(?:<=|<|max)?\s*(\d+(?:\.\d+)?)\s*%', "chemical", "Carbon Content"),
            (r'grade\s*(?:is|of|:)?\s*(33|43|53|fe\s*500d?|fe\s*550d?)', "general", "Grade Designation"),
        ]

        for pat, cat, param_name in param_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                unit = m.group(2).strip() if len(m.groups()) > 1 else None
                requirements.append({
                    "category": cat,
                    "parameter": param_name,
                    "operator": ">=" if "min" in lower or ">= " in text else "=",
                    "value": val,
                    "unit": unit,
                    "source_span": m.group(0),
                    "confidence": 0.95
                })

        return {
            "product_identity": product_identity,
            "application": application,
            "mentioned_standards": list(set(mentioned_standards)),
            "requirements": requirements
        }

    async def generate_recommendation_explanation(
        self, 
        query: str, 
        is_number: str, 
        title: str, 
        evidence_points: List[str]
    ) -> str:
        """
        Generates auditable, natural language explanation strictly from evidence.
        """
        evidence_str = "\n- ".join(evidence_points)
        prompt = (
            f"You are explaining why the Indian Standard {is_number} ({title}) was recommended for a procurement query.\n"
            f"User Query: {query}\n"
            f"Deterministic Evidence:\n- {evidence_str}\n\n"
            f"Write a concise 2-sentence explanation of why this standard applies. "
            f"Do not invent any details not provided in the evidence."
        )

        text = await self.generate_text(prompt)
        if text and text.strip():
            return text.strip()

        # Deterministic template fallback
        return f"{is_number} ({title}) applies directly to this procurement requirement based on technical parameter alignment, product scope definitions, and mandatory normative references."

llm_service = LLMService()
