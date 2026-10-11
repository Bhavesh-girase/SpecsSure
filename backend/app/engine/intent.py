"""
Intent Parser — turns an officer's one-line request into a structured procurement intent.

    "need a tender of 500 light bulbs and 100 meteres"
    "500 LED bulb 9 watt aur 100 meter 2.5 sq mm taar chahiye, 30 din mein, budget 2 lakh"
    "पाँच सौ बल्ब और सौ मीटर तार"

Deterministic first (works offline, auditable): number words (English / Hindi / Devanagari digits /
lakh-crore), typo-tolerant units (rapidfuzz), alias matching against the Procurement Knowledge Graph's item
layer, slot extraction (9 W, 2.5 sq mm, Fe 500D, B22, 4000 K, IP66 …).

What it cannot decide it *asks* — but only what matters: the questions are the item's mandatory slots that
are still empty (from the KG), plus a disambiguation question for quantities with no item ("100 metres of
what?") whose candidates are ranked with the KG's CO_PROCURED_WITH edges ("you're buying lamps → wiring cable").

An optional LLM pass (Gemini, when configured) may only *propose* items from the KG catalogue; its proposal is
validated against the catalogue and slot schema and shown as a suggestion, never silently applied.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from app.engine.kg import item_by_id, items

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "twenty five": 25, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "hundred": 100, "a hundred": 100, "thousand": 1000, "a thousand": 1000,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "बीस": 20, "पचास": 50, "सौ": 100, "हज़ार": 1000, "हजार": 1000,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "panch": 5, "das": 10, "bees": 20, "pachas": 50, "sau": 100, "hazaar": 1000, "hazar": 1000,
}
MULT = {"hundred": 100, "सौ": 100, "sau": 100, "thousand": 1000, "k": 1000, "हज़ार": 1000, "हजार": 1000, "hazar": 1000, "hazaar": 1000,
        "lakh": 100000, "lakhs": 100000, "lac": 100000, "लाख": 100000, "crore": 10000000, "cr": 10000000, "करोड़": 10000000}

QTY_UNITS = {
    "count": ["nos", "no", "no.", "nos.", "number", "numbers", "pcs", "pc", "piece", "pieces", "unit", "units", "set", "sets", "पीस", "नग"],
    "length": ["m", "meter", "meters", "metre", "metres", "mtr", "mtrs", "rmt", "running metre", "running meter", "मीटर", "km", "kilometre", "kilometer", "coil", "coils"],
    "mass": ["kg", "kgs", "kilogram", "kilograms", "tonne", "tonnes", "ton", "tons", "mt", "metric ton", "metric tonne", "quintal", "quintals", "bag", "bags", "टन", "बोरी", "किलो"],
}
UNIT_CANON = {"meter": "m", "meters": "m", "metre": "m", "metres": "m", "mtr": "m", "mtrs": "m", "rmt": "m", "running metre": "m", "running meter": "m", "मीटर": "m",
              "km": "km", "kilometre": "km", "kilometer": "km", "coil": "coil", "coils": "coil",
              "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg", "किलो": "kg", "tonne": "MT", "tonnes": "MT", "ton": "MT", "tons": "MT",
              "mt": "MT", "metric ton": "MT", "metric tonne": "MT", "टन": "MT", "quintal": "quintal", "quintals": "quintal", "bag": "bag", "bags": "bag", "बोरी": "bag"}
FILLER = r"\b(?:i|we|need|needs|want|wants|require|required|requirement|a|an|the|of|for|tender|tenders|please|kindly|make|create|generate|procure|purchase|buy|supply|chahiye|chahie|चाहिए|hai|hain|है|का|की|के|ke|ka|ki|with|new|some|about|approx|approximately|around)\b"
SPLIT = re.compile(r"\s*(?:,|;|\n|\+|&|\band\b|\balso\b|\bplus\b|\baur\b|\bor\s+also\b|\bऔर\b|\bतथा\b|\bसाथ\s+में\b)\s*", re.I)
SPEC_UNIT = r"(?:w\b|watt|watts|wp\b|sq\.?\s?mm|sqmm|mm2|mm²|mm\b|a\b|amp|amps|ka\b|k\b|kelvin|lm/w|star|kv\b|v\b|volt|%)"


@dataclass
class LineItem:
    index: int
    text: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    quantity_text: Optional[str] = None
    item_id: Optional[str] = None
    item_label: Optional[str] = None
    match: str = "none"                  # alias | fuzzy | inferred | llm | none
    confidence: float = 0.0
    candidates: List[dict] = field(default_factory=list)
    slots: Dict[str, object] = field(default_factory=dict)
    slot_sources: Dict[str, str] = field(default_factory=dict)   # slot -> "stated" | "default"
    notes: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def normalise(text: str) -> str:
    t = (text or "").translate(DEVANAGARI_DIGITS)
    t = re.sub(r"\b0f\b", "of", t, flags=re.I)                 # common typo: "0f" -> "of"
    t = t.replace("₹", " rs ").replace("’", "'")
    t = re.sub(r"(?<=\d),(?=\d{2,3}\b)", "", t)          # 1,00,000 -> 100000
    t = re.sub(r"(\d)\s*k\b(?!\s*(?:elvin|v))", lambda m: m.group(1) + "000", t, flags=re.I)  # 2k -> 2000 (not 4000 K!)
    return t


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.3f}".rstrip("0").rstrip(".")


def _word_numbers(t: str) -> str:
    # "five hundred" -> 500 ; "पाँच सौ" -> 500 ; "two lakh" -> 200000
    words = sorted(WORD_NUM, key=len, reverse=True)
    rx = re.compile(r"(?<![\wऀ-ॿ])(" + "|".join(re.escape(w) for w in words) + r")(?:\s+(" + "|".join(re.escape(m) for m in MULT) + r"))?(?![\wऀ-ॿ])", re.I)

    def rep(m):
        base = WORD_NUM[m.group(1).lower()] if m.group(1).lower() in WORD_NUM else WORD_NUM.get(m.group(1), 1)
        mult = MULT.get((m.group(2) or "").lower(), MULT.get(m.group(2) or "", 1))
        return _fmt(base * mult)
    t = rx.sub(rep, t)
    # numeric + multiplier: "2 lakh", "1.5 crore", "5 hundred"
    t = re.sub(r"(\d+(?:\.\d+)?)\s*(lakhs?|lac|लाख|crore|cr|करोड़|hundred|सौ|thousand|हज़ार|हजार)\b",
               lambda m: _fmt(float(m.group(1)) * MULT[m.group(2).lower() if m.group(2).lower() in MULT else m.group(2)]), t, flags=re.I)
    return t


def _fuzzy_unit(word: str) -> Optional[Tuple[str, str]]:
    w = word.lower().strip(".")
    for kind, us in QTY_UNITS.items():
        if w in us:
            return kind, UNIT_CANON.get(w, w if kind != "count" else "nos")
    if len(w) >= 4:
        best = None
        for kind, us in QTY_UNITS.items():
            for u in us:
                if len(u) >= 4:
                    sc = fuzz.ratio(w, u)
                    if sc >= 80 and (best is None or sc > best[0]):
                        best = (sc, kind, UNIT_CANON.get(u, u if kind != "count" else "nos"))
        if best:
            return best[1], best[2]
    return None


def _alias_index() -> List[Tuple[str, str]]:
    out = []
    for it in items():
        for a in it["aliases"] + [it["label"].lower()]:
            out.append((a.lower(), it["id"]))
    out.sort(key=lambda t: -len(t[0]))
    return out


def match_item(segment: str) -> Tuple[Optional[str], str, float, List[dict]]:
    s = " " + re.sub(r"\s+", " ", segment.lower()) + " "
    for alias, iid in _alias_index():
        if re.search(r"(?<![\wऀ-ॿ])" + re.escape(alias) + r"(?![\wऀ-ॿ])", s):
            return iid, "alias", 0.95 if len(alias) > 4 else 0.85, []
    # typo tolerance: compare each word-ngram with aliases
    words = re.findall(r"[a-zऀ-ॿ]+", s)
    grams = set(words) | {" ".join(words[i:i + 2]) for i in range(len(words) - 1)}
    best: Dict[str, float] = {}
    for g in grams:
        if len(g) < 4:
            continue
        for alias, iid in _alias_index():
            if len(alias) < 4:
                continue
            sc = fuzz.ratio(g, alias)
            if sc >= 84 and sc > best.get(iid, 0):
                best[iid] = sc
    if best:
        ranked = sorted(best.items(), key=lambda t: -t[1])
        iid, sc = ranked[0]
        return iid, "fuzzy", round(sc / 100 * 0.9, 2), [{"item_id": i, "score": round(s / 100, 2)} for i, s in ranked[1:4]]
    return None, "none", 0.0, []


# ------------------------------------------------------------------------------------------------ slots
def _num(s: str) -> float:
    return float(s)


def extract_slots(item_id: str, seg: str) -> Dict[str, object]:
    it = item_by_id(item_id)
    t = seg.lower()
    out: Dict[str, object] = {}
    ids = {s["id"] for s in it["slots"]}
    if "rated_power" in ids:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:w|watt|watts)\b", t)
        if m:
            out["rated_power"] = _num(m.group(1))
    if "module_power" in ids:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:wp|watt\s*peak|w)\b", t)
        if m:
            out["module_power"] = _num(m.group(1))
    if "conductor_area" in ids:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s?mm|sqmm|mm2|mm²|square\s*mm|sq)\b", t)
        if m:
            out["conductor_area"] = _num(m.group(1))
    if "cores" in ids:
        m = re.search(r"(\d)\s*[- ]?core", t)
        if m:
            out["cores"] = int(m.group(1))
        elif re.search(r"single[- ]core", t):
            out["cores"] = 1
    if "conductor_material" in ids:
        if re.search(r"alumin", t):
            out["conductor_material"] = "aluminium"
        elif re.search(r"copper|tamba|तांबा", t):
            out["conductor_material"] = "copper"
    if "insulation" in ids:
        if re.search(r"fr[- ]?lsh|frls|low smoke|lsh", t):
            out["insulation"] = "FR-LSH"
        elif re.search(r"\bfr\b|flame retardant", t):
            out["insulation"] = "FR"
    if "sweep" in ids:
        m = re.search(r"(900|1050|1200|1400)\s*(?:mm)?", t) or re.search(r"(\d{3,4})\s*mm", t)
        if m:
            out["sweep"] = int(m.group(1))
        elif re.search(r"48\s*(?:inch|\")", t):
            out["sweep"] = 1200
    if "sizes" in ids:
        m = re.findall(r"(\d{1,2})\s*mm", t)
        if m:
            out["sizes"] = sorted({int(x) for x in m})
    if "grade" in ids:
        m = re.search(r"fe\s?(500|550|415)\s?(d)?", t)
        if m:
            out["grade"] = f"Fe {m.group(1)}{'D' if m.group(2) else ''}"
        m = re.search(r"\b(33|43|53)\s*(?:grade)?\b|grade\s*(33|43|53)", t)
        if m and item_id == "opc_cement":
            out["grade"] = m.group(1) or m.group(2)
    if "cap_type" in ids:
        if re.search(r"\bb\s?22", t) or re.search(r"pin\s*type|bayonet", t):
            out["cap_type"] = "B22d"
        elif re.search(r"\be\s?27\b|screw", t):
            out["cap_type"] = "E27"
    if "cct" in ids:
        m = re.search(r"(2700|3000|4000|5000|5700|6500)\s*k\b", t)
        if m:
            out["cct"] = int(m.group(1))
        elif re.search(r"warm", t):
            out["cct"] = 2700
        elif re.search(r"neutral", t):
            out["cct"] = 4000
        elif re.search(r"cool|day\s?light|white light", t):
            out["cct"] = 6500
    if "star_rating" in ids:
        m = re.search(r"([1-5])\s*[- ]?star", t)
        if m:
            out["star_rating"] = int(m.group(1))
    if "ip" in ids:
        m = re.search(r"\bip\s?(65|66|67)\b", t)
        if m:
            out["ip"] = f"IP{m.group(1)}"
    if "rated_current" in ids:
        m = re.search(r"(\d{1,3})\s*(?:a|amp|amps|ampere)\b", t)
        if m:
            out["rated_current"] = int(m.group(1))
    if "poles" in ids:
        m = re.search(r"\b(sp|dp|tp|tpn)\b|(single|double|triple)[- ]pole", t)
        if m:
            out["poles"] = (m.group(1) or {"single": "sp", "double": "dp", "triple": "tp"}[m.group(2)]).upper()
    if "curve" in ids:
        m = re.search(r"\b([bcd])[- ]?(?:curve|type|characteristic)\b", t)
        if m:
            out["curve"] = m.group(1).upper()
    return out


# ------------------------------------------------------------------------------------------------ main
def _globals(t: str) -> dict:
    g: Dict[str, object] = {}
    m = re.search(r"(?:budget|estimated(?:\s+value|\s+cost)?|cost|within|under|upto|up to|limit|बजट)\s*(?:of|is|:)?\s*(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees|/-)?", t, re.I)
    if m and float(m.group(1)) >= 1000:
        g["budget_inr"] = float(m.group(1))
    m = re.search(r"(?:within|in|inside|मैं|में|me)\s*(\d{1,3})\s*(days?|din|दिन|weeks?|hafte|हफ्ते|months?|mahine|महीने)", t, re.I) or \
        re.search(r"(\d{1,3})\s*(days?|din|दिन|weeks?|hafte|हफ्ते|months?|mahine|महीने)\s*(?:mein|me|में|ke andar|के अंदर|within|delivery)?", t, re.I)
    if m:
        n = int(m.group(1))
        u = m.group(2).lower()
        g["delivery_days"] = n * (7 if u.startswith(("week", "haft", "हफ")) else 30 if u.startswith(("month", "mahin", "मही")) else 1)
    m = re.search(r"\bfor\s+(?:the\s+|our\s+)?([A-Za-z][\w .\-/]{3,60}?)(?=,|\.|;|$|\s+(?:within|in\s+\d|budget|deliver))", t)
    if m and not re.search(r"^(?:tender|supply|procurement)\b", m.group(1), re.I):
        g["purpose"] = m.group(1).strip()
    m = re.search(r"(?:deliver(?:ed|y)?\s+(?:to|at)|at)\s+([A-Z][\w .\-/]{3,60}?)(?=,|\.|;|$|\s+(?:within|in\s+\d|budget))", t)
    if m:
        g["delivery_place"] = m.group(1).strip()
    return g


def parse(text: str) -> dict:
    raw = text or ""
    t = _word_numbers(normalise(raw))
    glob = _globals(t)
    # remove global phrases from item parsing
    body = re.sub(r"(?:budget|estimated(?:\s+value|\s+cost)?|बजट)\s*(?:of|is|:)?\s*(?:rs\.?|inr)?\s*\d+(?:\.\d+)?\s*(?:rs|rupees|/-)?", " ", t, flags=re.I)
    body = re.sub(r"(?:(?:within|in|inside|में|me)\s*)?\d{1,3}\s*(?:days?|din|दिन|weeks?|hafte|हफ्ते|months?|mahine|महीने)(?:\s*(?:mein|me|में|ke andar|के अंदर))?", " ", body, flags=re.I)
    segments = [s.strip() for s in SPLIT.split(body) if s and s.strip()]
    lines: List[LineItem] = []
    for seg in segments:
        clean = re.sub(FILLER, " ", seg, flags=re.I)
        clean = re.sub(r"\s+", " ", clean).strip(" .:-")
        if not clean:
            continue
        # quantity: a number NOT followed by a spec unit
        qty, unit, qtext = None, None, None
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([a-zA-Zऀ-ॿ.]+(?:\s+(?:metre|meter|ton|tonne))?)?", clean):
            after = clean[m.end(1):m.end(1) + 12].lower()
            if re.match(r"\s*" + SPEC_UNIT, after, re.I):
                # "9 w" etc. is a slot, not a quantity — unless it's a qty unit like "m" (metres)
                u = _fuzzy_unit((m.group(2) or "").split(" ")[0])
                if not u:
                    continue
            u = _fuzzy_unit((m.group(2) or "").split(" ")[0]) if m.group(2) else None
            if float(m.group(1)) <= 0:
                continue
            qty = float(m.group(1))
            qtext = m.group(0).strip()
            unit = u[1] if u else None
            break
        iid, how, conf, cands = match_item(clean)
        li = LineItem(index=len(lines) + 1, text=seg, quantity=qty, unit=unit, quantity_text=qtext, item_id=iid, match=how,
                      confidence=conf, candidates=cands)
        if iid is None and qty is None:
            # attribute-only fragment ("9 watt", "2.5 sq mm") -> attach to the previous line item
            if lines and lines[-1].item_id:
                extra = extract_slots(lines[-1].item_id, clean)
                if extra:
                    lines[-1].slots.update(extra)
                    lines[-1].slot_sources.update({k: "stated" for k in extra})
                    continue
            if not re.search(r"[a-zऀ-ॿ]{3,}", clean, re.I):
                continue
        lines.append(li)

    # resolve line items: slots, units, orphans
    resolved = [l.item_id for l in lines if l.item_id]
    for li in lines:
        if li.item_id is None and li.quantity is not None:
            kind = next((k for k, us in QTY_UNITS.items() if li.unit and (li.unit in us or li.unit in [UNIT_CANON.get(x) for x in us])), None)
            if li.unit in ("m", "km", "coil"):
                kind = "length"
            elif li.unit in ("kg", "MT", "quintal", "bag"):
                kind = "mass"
            cands = []
            for it in items():
                if kind and it["unit_kind"] != kind:
                    continue
                score, why = 0.3, []
                for r in resolved:
                    rit = item_by_id(r)
                    if it["id"] in (rit.get("related") or []) or r in (it.get("related") or []):
                        score += 0.4
                        why.append(f"often bought with {rit['label'].split('(')[0].strip()}")
                    if rit["domain"] == it["domain"]:
                        score += 0.1
                if kind:
                    score += 0.2
                    why.append(f"sold by {'length' if kind == 'length' else 'weight' if kind == 'mass' else 'count'}")
                cands.append({"item_id": it["id"], "label": it["label"], "score": round(min(score, 0.99), 2), "why": "; ".join(why)})
            cands.sort(key=lambda c: -c["score"])
            li.candidates = cands[:4]
            if cands:
                li.item_id = cands[0]["item_id"]
                li.match = "inferred"
                li.confidence = cands[0]["score"] * (0.8 if len(cands) == 1 else 0.6)
                li.notes.append(f"No item named for '{li.quantity_text}'. Inferred '{cands[0]['label']}' ({cands[0]['why']}). Please confirm.")
        if li.item_id:
            it = item_by_id(li.item_id)
            li.item_label = it["label"]
            stated = extract_slots(li.item_id, li.text)
            li.slots.update({k: v for k, v in stated.items() if k not in li.slots})
            li.slot_sources.update({k: "stated" for k in stated})
            if li.unit is None:
                li.unit = it["default_unit"]
                if li.quantity is not None:
                    li.notes.append(f"Unit not stated; assumed {it['default_unit']}.")
            # unit conversions to the item's unit of account
            if li.quantity is not None:
                if li.unit == "km":
                    li.quantity, li.unit = li.quantity * 1000, "m"
                if li.unit == "coil" and it.get("pack") and it["pack"]["unit"] == "m":
                    li.quantity, li.unit = li.quantity * it["pack"]["size"], "m"
                    li.notes.append(f"Converted coils to metres ({it['pack']['label']}).")
                if li.unit == "bag" and li.item_id == "opc_cement":
                    li.notes.append(f"{li.quantity:g} bags × 50 kg = {li.quantity * 0.05:g} MT.")
                    li.quantity, li.unit = round(li.quantity * 0.05, 3), "MT"
                if li.unit == "quintal":
                    li.quantity, li.unit = li.quantity / 10, "MT"
                if li.unit == "kg" and it["default_unit"] == "MT":
                    li.quantity, li.unit = li.quantity / 1000, "MT"
                if li.unit == "nos" and it["unit_kind"] == "length":
                    li.notes.append("Quantity given as a count for an item sold by length — please confirm metres.")
                if it.get("pack") and it["pack"]["unit"] == li.unit and li.quantity and it["pack"]["size"] >= 1:
                    packs = li.quantity / it["pack"]["size"]
                    if abs(packs - round(packs)) > 0.01:
                        li.notes.append(f"{li.quantity:g} {li.unit} = {packs:.2f} × {it['pack']['label']}; the tender will ask for standard coils plus one cut length.")

    # questions — only what matters
    questions = []
    for li in lines:
        if li.item_id is None:
            questions.append({"id": f"L{li.index}.item", "line": li.index, "slot": "item", "type": "choice", "required": True,
                              "question": f"What is '{li.text.strip()}'?", "options": [{"value": it["id"], "label": it["label"]} for it in items()],
                              "why": "The item decides which standards, certifications and tests apply."})
            continue
        if li.match == "inferred":
            questions.append({"id": f"L{li.index}.item", "line": li.index, "slot": "item", "type": "choice", "required": True,
                              "question": f"{li.quantity_text} of what?", "default": li.item_id,
                              "options": [{"value": c["item_id"], "label": c["label"], "why": c["why"]} for c in li.candidates]
                                         + [{"value": it["id"], "label": it["label"], "why": "other item"} for it in items()
                                            if it["id"] not in {c["item_id"] for c in li.candidates}],
                              "why": "Ranked using the knowledge graph: items sold by the same unit and usually procured together with the rest of your request."})
        if li.quantity is None:
            questions.append({"id": f"L{li.index}.quantity", "line": li.index, "slot": "quantity", "type": "number", "required": True,
                              "question": f"How many / how much {item_by_id(li.item_id)['label']} ({item_by_id(li.item_id)['default_unit']})?"})
        it = item_by_id(li.item_id)
        for sl in it["slots"]:
            if sl["id"] in li.slots:
                continue
            if sl.get("ask"):
                questions.append({"id": f"L{li.index}.{sl['id']}", "line": li.index, "slot": sl["id"], "type": sl["type"], "required": True,
                                  "question": sl.get("question") or sl["label"], "question_hi": sl.get("question_hi"),
                                  "options": sl.get("options"), "default": sl.get("default"), "unit": sl.get("unit"), "why": sl.get("why")})
            li.slots.setdefault(sl["id"], sl.get("default"))
            li.slot_sources.setdefault(sl["id"], "default")
    lang = "hi" if re.search(r"[ऀ-ॿ]", raw) else ("hinglish" if re.search(r"\b(chahiye|aur|taar|din|mein|wala|wali)\b", raw, re.I) else "en")
    return {"input": raw, "normalised": t, "language": lang, "line_items": [l.to_dict() for l in lines], "globals": glob,
            "questions": questions, "parser": "deterministic", "complete": not any(q["required"] and "default" not in q for q in questions)}


def apply_answers(intent: dict, answers: Dict[str, object]) -> dict:
    """answers: {"L2.item": "pvc_cable", "L2.conductor_area": 2.5, "L1.quantity": 500, "globals.delivery_days": 30}"""
    for li in intent["line_items"]:
        for k, v in answers.items():
            if not k.startswith(f"L{li['index']}."):
                continue
            slot = k.split(".", 1)[1]
            if slot == "item":
                if v != li.get("item_id"):
                    li["item_id"] = v
                    it = item_by_id(v)
                    li["item_label"] = it["label"]
                    li["slots"] = {**{s["id"]: s.get("default") for s in it["slots"]}, **extract_slots(v, li["text"])}
                    li["slot_sources"] = {s["id"]: "default" for s in it["slots"]}
                    if li.get("unit") is None:
                        li["unit"] = it["default_unit"]
                li["match"] = "confirmed"
                li["confidence"] = 1.0
            elif slot == "quantity":
                li["quantity"] = float(v)
            else:
                li["slots"][slot] = v
                li["slot_sources"][slot] = "answered"
    for k, v in answers.items():
        if k.startswith("globals."):
            intent["globals"][k.split(".", 1)[1]] = v
    intent["questions"] = []
    intent["complete"] = all(li.get("item_id") and li.get("quantity") for li in intent["line_items"])
    return intent


async def llm_suggest(text: str) -> Optional[dict]:
    """Optional: ask the LLM to map the request onto KG items. Output is validated; never auto-applied."""
    import json
    import os
    if os.getenv("SPECSURE_LLM_INTENT", "0") != "1":
        return None
    try:
        from app.services.llm_service import LLMService
        from app.engine.guardrails import scan_injection
        llm = LLMService()
        if not llm.is_available() or scan_injection(text):
            return None
        catalogue = {it["id"]: {"label": it["label"], "slots": [s["id"] for s in it["slots"]]} for it in items()}
        prompt = ("Map the procurement request to catalogue items. Reply ONLY with JSON: "
                  '{"items":[{"item_id":"<catalogue id>","quantity":<number>,"unit":"<nos|m|MT>","slots":{"<slot id>":<value>}}]}.\n'
                  f"Catalogue: {json.dumps(catalogue)}\n<request>{text[:600]}</request>")
        out = await llm.generate_text(prompt, "You map procurement requests to a fixed catalogue. Never invent item ids.")
        m = re.search(r"\{.*\}", out or "", re.S)
        data = json.loads(m.group(0)) if m else None
        if not data:
            return None
        valid = [i for i in data.get("items", []) if i.get("item_id") in catalogue]
        for i in valid:
            i["slots"] = {k: v for k, v in (i.get("slots") or {}).items() if k in catalogue[i["item_id"]]["slots"]}
        return {"items": valid, "model": "gemini", "note": "LLM suggestion validated against the KG catalogue — not applied automatically."}
    except Exception:
        return None
