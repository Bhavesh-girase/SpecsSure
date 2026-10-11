import re
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

# Common Hindi / Indic technical domain translations for procurement terms
INDIAN_PROCUREMENT_VOCAB: Dict[str, str] = {
    "सीमेंट": "cement",
    "पोर्टलैंड": "portland",
    "ग्रेड": "grade",
    "स्टील": "steel",
    "सरिया": "steel reinforcement bar TMT",
    "तार": "wire",
    "केबल": "cable",
    "तांबा": "copper",
    "एल्यूमीनियम": "aluminum",
    "पानी": "drinking water",
    "पाइप": "pipe",
    "प्लास्टिक": "plastic",
    "रासायनिक": "chemical",
    "विद्युत": "electrical",
    "ऊर्जा": "energy",
    "गुणवत्ता": "quality",
    "परीक्षण": "test method testing",
    "मोटाई": "thickness",
    "व्यास": "diameter",
    "दबाव": "pressure compressive strength",
    "तन्यता": "tensile strength",
    "टिकाऊ": "durable",
    "सुरक्षा": "safety standard",
    "मानक": "standard",
    "खरीद": "procurement tender",
    "निविदा": "tender",
    "सामग्री": "material",
    "आपूर्ति": "supply",
    "पीने": "potable drinking", "पेयजल": "potable drinking water", "एचडीपीई": "HDPE high density polyethylene", "पीवीसी": "PVC polyvinyl chloride",
    "बल्ब": "lamp LED", "एलईडी": "LED", "पंखा": "ceiling fan", "पंखे": "fans", "हेलमेट": "helmet", "अग्निशामक": "fire extinguisher",
    "ईंट": "bricks", "ईंटें": "bricks", "पेंट": "paint", "रंग": "paint", "जूते": "footwear shoes", "टंकी": "water storage tank",
    "गैस": "gas", "सिलेंडर": "cylinder", "मीटर": "meter", "बिजली": "electricity electrical", "ट्रांसफार्मर": "transformer",
    "कुकर": "pressure cooker", "सौर": "solar photovoltaic", "पैनल": "panel module", "स्विच": "switches", "सॉकेट": "socket outlets",
    "दोपहिया": "two wheeler", "वाहन": "motor vehicle", "चालकों": "riders", "चालक": "riders", "यंत्र": "apparatus equipment",
    "घरेलू": "domestic household", "पंखा": "ceiling fan", "छत": "ceiling roof", "तांबे": "copper", "नाली": "drain", "छत": "roof",
    # Tamil
    "கம்பி": "wire", "கேபிள்": "cable", "குழாய்": "pipe", "சிமெண்ட்": "cement", "எஃகு": "steel", "செப்பு": "copper", "மின்": "electrical",
    "விளக்கு": "lamp", "மின்விசிறி": "ceiling fan", "தலைக்கவசம்": "helmet", "குடிநீர்": "potable drinking water", "தீயணைப்பான்": "fire extinguisher",
    "வீட்டு": "house domestic", "இணைப்பு": "wiring connection", "தண்ணீர்": "water", "செங்கல்": "bricks",
    # Telugu
    "తీగ": "wire", "కేబుల్": "cable", "పైపు": "pipe", "సిమెంట్": "cement", "ఉక్కు": "steel", "రాగి": "copper", "బల్బ్": "lamp",
    "ఎల్ఈడి": "LED", "ఫ్యాన్": "ceiling fan", "హెల్మెట్": "helmet", "తాగునీరు": "potable drinking water", "నీరు": "water", "విద్యుత్": "electrical",
    # Bengali
    "তার": "wire", "পাইপ": "pipe", "সিমেন্ট": "cement", "ইস্পাত": "steel", "তামা": "copper", "বাল্ব": "lamp", "পাখা": "ceiling fan",
    "হেলমেট": "helmet", "পানীয়": "potable drinking", "জল": "water", "বিদ্যুৎ": "electrical",
    # Kannada
    "ಅಗ್ನಿಶಾಮಕ": "fire extinguisher", "ತಂತಿ": "wire", "ಪೈಪ್": "pipe", "ಸಿಮೆಂಟ್": "cement", "ಉಕ್ಕು": "steel", "ನೀರು": "water",
    "कंक्रीट": "concrete", "रेत": "sand", "गिट्टी": "coarse aggregate", "लोहा": "iron steel", "चादर": "sheet", "नल": "tap water fittings"
}
# ---- extended procurement glossary (native words; English loanwords written in Indic script are handled by translit.py)
EXTRA_VOCAB: Dict[str, str] = {
    # Hindi — furniture & office
    "कुर्सी": "chair", "कुर्सियाँ": "chairs", "मेज": "table", "मेज़": "table", "अलमारी": "steel cupboard cabinet almirah", "अलमारियाँ": "cupboards",
    "तिजोरी": "safes", "बेंच": "bench", "पलंग": "bed", "चारपाई": "cot bed", "गद्दा": "mattress", "गद्दे": "mattresses", "तकिया": "pillow",
    "रजिस्टर": "register", "कागज": "paper", "कागज़": "paper", "लिफाफा": "envelopes", "लिफाफे": "envelopes", "कलम": "pen", "पेंसिल": "pencils",
    "स्याही": "ink", "फाइल": "file folder", "गोंद": "adhesive", "कार्यालय": "office", "ऑफिस": "office", "दफ्तर": "office",
    # Hindi — household, textiles, hygiene
    "बाल्टी": "bucket", "झाड़ू": "broom", "पोछा": "mop", "साबुन": "soap", "कंबल": "blanket", "कम्बल": "blanket", "चादर": "sheet bedsheet",
    "तौलिया": "towel", "दरी": "durries", "कपड़ा": "fabric cloth", "कपड़े": "fabric cloth", "वर्दी": "uniform", "दस्ताने": "gloves",
    "मास्क": "mask", "जूता": "footwear shoes", "जूते": "footwear shoes", "चप्पल": "slippers footwear", "बर्तन": "utensils", "थाली": "plate",
    "गिलास": "tumbler", "चूल्हा": "stove", "कुकर": "pressure cooker", "बोतल": "bottle", "छाता": "umbrella", "ताला": "padlock lock", "ताले": "locks",
    "रस्सी": "rope", "जाल": "net", "तिरपाल": "tarpaulin", "तंबू": "tent", "बोरी": "bag sack", "बोरा": "gunny bag", "थैला": "bag",
    # Hindi — construction & materials
    "सीढ़ी": "ladder", "दरवाजा": "door", "दरवाज़ा": "door", "खिड़की": "window", "शीशा": "glass", "कांच": "glass", "टाइल": "tiles",
    "पत्थर": "stone", "बजरी": "aggregate", "मिट्टी": "soil clay", "चूना": "lime", "लकड़ी": "timber wood", "बांस": "bamboo",
    "जस्ता": "zinc galvanized", "लोहे": "iron steel", "लोहे की": "steel", "पीतल": "brass copper alloy", "कांसा": "bronze",
    "कांटेदार": "barbed", "जाली": "mesh", "छड़": "bars rods", "छड़ें": "bars rods", "नाला": "drain", "सड़क": "road", "सड़कों": "roads",
    "पुल": "bridge", "खंभा": "pole", "खंभे": "poles", "ढक्कन": "cover", "टंकी": "water storage tank", "कुआं": "well", "हैंडपंप": "hand pump",
    # Hindi — electrical, energy, machines
    "बत्ती": "lamp light", "रोशनी": "lighting", "प्रकाश": "lighting", "तार": "wire", "मीटर": "watthour meter", "पंप": "pump", "मोटर": "motor",
    "जनरेटर": "generator", "इस्त्री": "electric iron", "हीटर": "heater", "गीजर": "storage water heater", "कूलर": "cooler",
    "ठंडा": "cooler", "शीतल": "cooler", "वितरण": "distribution", "उपकरण": "equipment", "मशीन": "machine", "वाहन": "motor vehicle",
    "टायर": "tyres", "ट्यूब": "tubes", "तेल": "oil", "डीजल": "diesel", "मिट्टी का तेल": "kerosene", "सौर": "solar photovoltaic",
    # Hindi — safety, medical
    "अग्निशमन": "fire fighting", "आग": "fire", "प्राथमिक": "first aid", "चिकित्सा": "medical", "दवा": "medicine", "पट्टी": "bandage",
    "रुई": "cotton wool", "सुई": "needle syringe", "सिरिंज": "syringe", "थर्मामीटर": "thermometer", "सर्जिकल": "surgical", "रक्षा": "protective",
    "सुरक्षात्मक": "protective safety", "बचाव": "protective",
    # Hindi — agriculture
    "खाद": "fertilizer", "उर्वरक": "fertilizer", "बीज": "seeds", "कीटनाशक": "pesticide insecticide", "छिड़काव": "sprayer", "ट्रैक्टर": "tractor",
    # Hindi — qualifiers
"लोहा": "iron steel", "इस्पात": "steel", "प्लास्टिक": "plastic", "रबर": "rubber", "एयर": "air", "ऑयल": "oil",
    "गैस": "gas", "पोर्टेबल": "portable", "बैटरी": "battery", "बैटरियां": "batteries", "फर्स्ट एड": "first aid", "एड": "aid", "घर": "household domestic", "सरकारी": "government",
    # Marathi
    "पाणी": "water", "पाण्याची": "water", "टाकी": "storage tank", "छताचा": "ceiling", "खुर्ची": "chair", "कपाट": "cupboard", "वीज": "electricity",
    "विद्युत": "electrical", "पाईप": "pipe", "दिवा": "lamp", "रस्ता": "road", "लोखंडी": "iron steel", "शिडी": "ladder", "कागद": "paper",
    # Tamil
    "நாற்காலி": "chair", "மேசை": "table", "அலமாரி": "cupboard", "இரும்பு": "iron steel", "மின்சார": "electrical", "மீட்டர்": "meter",
    "தண்ணீர்": "water", "தொட்டி": "tank", "காகிதம்": "paper", "கையுறை": "gloves", "காலணி": "footwear", "போர்வை": "blanket",
    "குளிர்விப்பான்": "cooler", "சாலை": "road", "ஏணி": "ladder", "பூட்டு": "lock", "சோப்பு": "soap",
    # Telugu
    "కుర్చీ": "chair", "బల్ల": "table", "బీరువా": "cupboard almirah", "ఇనుప": "iron steel", "కడ్డీలు": "bars rods", "నీటి": "water",
    "ట్యాంకు": "tank", "కాగితం": "paper", "చేతి తొడుగులు": "gloves", "చెప్పులు": "footwear", "దుప్పటి": "blanket", "రోడ్డు": "road",
    "నిచ్చెన": "ladder", "తాళం": "lock", "సబ్బు": "soap", "మీటర్": "meter", "విద్యుత్": "electrical",
    # Bengali
    "চেয়ার": "chair", "টেবিল": "table", "আলমারি": "cupboard almirah", "স্টিলের": "steel", "লোহার": "iron steel", "বিদ্যুতের": "electricity meter",
    "মিটার": "meter", "জলের": "water", "ট্যাঙ্ক": "tank", "কাগজ": "paper", "দস্তানা": "gloves", "জুতো": "footwear", "কম্বল": "blanket",
    "রাস্তা": "road", "মই": "ladder", "তালা": "lock", "সাবান": "soap", "অগ্নি": "fire", "নির্বাপক": "extinguisher",
    # Kannada
    "ಕುರ್ಚಿ": "chair", "ಮೇಜು": "table", "ಕಪಾಟು": "cupboard", "ಕಬ್ಬಿಣ": "iron steel", "ನೀರಿನ": "water", "ಟ್ಯಾಂಕ್": "tank", "ಕಾಗದ": "paper",
    "ಕೈಗವಸು": "gloves", "ಹೊದಿಕೆ": "blanket", "ರಸ್ತೆ": "road", "ಏಣಿ": "ladder", "ಬೀಗ": "lock", "ಸಾಬೂನು": "soap", "ವಿದ್ಯುತ್": "electrical",
}
INDIAN_PROCUREMENT_VOCAB.update(EXTRA_VOCAB)


def detect_language(text: str) -> str:
    """
    Detects language from text by analyzing Unicode script character distributions.
    Returns ISO 639-1 code ('hi', 'ta', 'te', 'bn', 'en', etc.).
    """
    if not text:
        return "en"

    # Count script character occurrences
    devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
    tamil_count = len(re.findall(r'[\u0B80-\u0BFF]', text))
    telugu_count = len(re.findall(r'[\u0C00-\u0C7F]', text))
    bengali_count = len(re.findall(r'[\u0980-\u09FF]', text))
    
    total_indic = devanagari_count + tamil_count + telugu_count + bengali_count
    
    if devanagari_count > 5 or (total_indic > 0 and devanagari_count >= total_indic * 0.5):
        return "hi"
    elif tamil_count > 5:
        return "ta"
    elif telugu_count > 5:
        return "te"
    elif bengali_count > 5:
        return "bn"
    elif len(re.findall(r'[\u0C80-\u0CFF]', text)) > 3:
        return "kn"
    
    return "en"

async def translate_to_english(text: str, source_lang: str) -> Tuple[str, bool]:
    """
    Translates Indic or multilingual text to English.
    Preserves all technical terms, IS standard citations, and numbers.
    Returns (translated_text, was_translated).
    """
    if source_lang == "en" or not text.strip():
        return text, False

    # Attempt LLM translation via Gemini
    try:
        from app.services.llm_service import llm_service
        if llm_service.is_available():
            prompt = (
                f"You are a specialized government procurement and technical translation assistant for Indian Standards.\n"
                f"Translate the following tender / technical specification from {source_lang} into English.\n"
                f"RULES:\n"
                f"1. Preserve all IS numbers (e.g. 'IS 269', 'IS 1786') and numerical measurements verbatim.\n"
                f"2. Translate technical material names accurately (e.g. 'सीमेंट' -> 'cement', 'सरिया' -> 'TMT steel rebar').\n"
                f"3. Return ONLY the English translation with no extra commentary or conversational filler.\n\n"
                f"Input text:\n{text}"
            )
            translated = await llm_service.generate_text(prompt)
            if translated and translated.strip():
                return translated.strip(), True
    except Exception as e:
        logger.warning(f"LLM translation failed, applying dictionary fallback: {e}")

    # Vocabulary-assisted transliteration / keyword augmentation fallback
    return lexicon_translate(text)[0], True


def lexicon_translate(text: str):
    """Offline fallback: procurement glossary (exact → agglutinative prefix) → loanword matcher for English technical
    words written in Indic script. Returns ("word (english) …", trace) where trace lists how each word was read."""
    from app.services import translit
    words = text.split()
    clean = [w.strip(".,;:!?()[]{}\"'।") for w in words]
    keys = sorted(INDIAN_PROCUREMENT_VOCAB, key=len, reverse=True)
    hits, trace = [None] * len(words), [None] * len(words)
    for i, cw in enumerate(clean):
        h = INDIAN_PROCUREMENT_VOCAB.get(cw)
        if h is None and i + 1 < len(clean):
            h2 = INDIAN_PROCUREMENT_VOCAB.get(cw + " " + clean[i + 1])
            if h2:
                h = h2
        if h is not None:
            hits[i], trace[i] = h, {"word": cw, "english": h, "via": "glossary"}
    loan = translit.read_words([cw if hits[i] is None and translit.script_of(cw) else "" for i, cw in enumerate(clean)])
    for i, cw in enumerate(clean):
        if hits[i] is not None or not cw:
            continue
        if loan[i]:
            hits[i] = loan[i]["english"]
            trace[i] = {"word": cw, "english": hits[i], "via": "acronym" if loan[i]["key"] == "acronym" else "transliteration",
                        "roman": loan[i].get("roman"), "skeleton": loan[i].get("key")}
            continue
        h = next((INDIAN_PROCUREMENT_VOCAB[k] for k in keys if len(k) >= 3 and cw.startswith(k)), None)   # இணைப்புக்கான → இணைப்பு
        if h:
            hits[i], trace[i] = h, {"word": cw, "english": h, "via": "glossary (stem)"}
    out = [f"{w} ({h})" if h else w for w, h in zip(words, hits)]
    return " ".join(out), [t for t in trace if t]
