"""
Procurement-item extraction from real tender documents.

Real tenders are 20–200 pages of which a few rows describe what is actually bought. Recommending standards from every
paragraph produces noise, so we first find the items:

  1. item tables — a header with a description column (Description / Name of Item / Name of Equipment / Particulars /
     Nomenclature …) and usually a quantity column; each following row with a description is an item
  2. "Supply of …" / "Providing and fixing …" / "Procurement of …" lines (works tenders and single-item NITs)
  3. the technical-specification section under each item (lines after a "Technical Specification" / "Schedule of
     Requirement" heading), kept as context

Administrative rows (EMD, bid validity, documents checklists, signatures) are filtered out.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

DESC_HEAD = re.compile(r"\b(description|name of (?:the )?(?:item|equipment|goods|material|article|store|product|instrument)s?|item(?:s)?(?: name| description)?|"
                       r"particulars|nomenclature|details of (?:item|goods|material)|material|product|equipment)\b", re.I)
QTY_HEAD = re.compile(r"\b(qty|quantity|quan\.?|no\.? of|nos?\.?|units?|uom)\b", re.I)
ADMIN = re.compile(r"\b(emd|earnest|bid (?:security|validity)|performance security|tender fee|document(?:s)? to be|upload|signature|signed|witness|"
                   r"pan|gst(?:in)?|registration certificate|turnover|experience|authori[sz]ation|undertaking|affidavit|letter head|bank|"
                   r"cmc charges|amc charges|year of manufacture|make\s*:|model\s*:|country of origin|rate per|total cost|price|amount|"
                   r"annexure|page no|e-?tender|cppp|eprocure|last date|opening|schedule of dates|particulars of bidder|name of bidder|"
                   r"refer page|instructions to bidders|general terms|conditions of contract)\b", re.I)
SUPPLY_RE = re.compile(r"(?:^|\n)\s*(?:\d{1,3}[.)]\s*)?((?:supply|supplying)(?:,?\s*(?:installation|installing|testing|commissioning|fixing|erection)(?: and| &|,)?)*\s+of"
                       r"|providing\s+(?:and|&)\s+(?:fixing|laying|applying|supplying)|procurement of|purchase of)\s+([^\n]{6,220})", re.I)
SPEC_HEAD = re.compile(r"(technical\s+specifications?|schedule\s+of\s+requirements?|scope\s+of\s+supply|specifications?\s+of\s+(?:the\s+)?(?:item|equipment|goods)|"
                       r"bill\s+of\s+quantit(?:y|ies)|boq|list\s+of\s+(?:items|goods|equipment))", re.I)
UNIT_RE = re.compile(r"\b(\d[\d,.]*)\s*(nos?\.?|numbers?|sets?|pcs|pieces|pairs?|units?|m|mtrs?|metres?|meters?|km|kg|mt|tonnes?|tons?|litres?|l|kl|"
                     r"sqm|sq\.?\s?m|cum|rm|lots?|each|bags?|rolls?|coils?|boxes|packets?)\b", re.I)


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip(" .:-–|")
    return s


NOT_ITEM_START = re.compile(r"^(whether|is |are |does |do |can |could |has |have |documents?|any other|manual|literatures?|all |the |copy|copies|"
                            r"details|name of|proof|certificates?|undertaking|list of|scope|terms|note|if |in case|bidder|tenderer|vendor|"
                            r"the system|please|kindly|buy[- ]?back|goods by|creating|bidders?|sellers?|service providers?)\b", re.I)
GENERIC = re.compile(r"^(goods|items?|materials?|equipments?|stores?|the following|various|following items?|articles?|works?|plant|plants|"
                     r"plant\s*/\s*equipment\s*/\s*material|proforma[\w\s]*|schedule[\w\s]*)\b[\s.,(]*"
                     r"(\(hereinafter.*|as per.*|mentioned.*|listed.*)?$", re.I)


ATTRIBUTE = re.compile(r"^(?:[\w/&().-]+\s){0,2}?(wattage|voltage|input|output|efficacy|flux|housing|body|classification|rating|ratings|capacity|"
                       r"make|model|warranty|dimensions?|weight|colou?r|finish|material of construction|power factor|frequency|thd|cri|cct|"
                       r"ip rating|protection|general specifications?|specifications?|features?|parameters?|type|size|quantity|standard|standards|"
                       r"accessories|operating temperature|mounting|lumen|lumens|surge|driver|life|efficiency|certification)s?\b[\w\s/().-]{0,20}$", re.I)
SPEC_TABLE_HEAD = re.compile(r"\b(parameter|feature|attribute|specification required|technical parameter|characteristic|compliance|complied|"
                             r"offered|bidder'?s? (?:response|offer))\b", re.I)


def _strip_numbering(s: str) -> str:
    return re.sub(r"^\(?(?:[ivxlc]{1,5}|\d{1,3}|[a-z])[.)]\s+", "", s, flags=re.I).strip()


def _is_item_text(s: str) -> bool:
    if len(s) < 4 or len(s) > 400 or not re.search(r"[A-Za-z]{3,}", s):
        return False
    if s.rstrip().endswith("?") or NOT_ITEM_START.search(s) or GENERIC.search(s):
        return False
    if len(s.split()) <= 4 and ATTRIBUTE.search(s):
        return False                      # a specification attribute ("Wattage", "Input Voltage"), not an item
    if ADMIN.search(s):
        return False
    if re.fullmatch(r"(total|grand total|sub[- ]?total|gst|taxes|freight|note|remarks?)[\s:]*.*", s, re.I):
        return False
    return True


def items_from_tables(pages: List[dict]) -> List[dict]:
    out = []
    for p in pages:
        for t in p.get("tables") or []:
            if not t:
                continue
            head = [_clean(c) for c in t[0]]
            if any(SPEC_TABLE_HEAD.search(h) for h in head):
                continue                          # a parameter / compliance table describes one item, it does not list items
            cands = [i for i, h in enumerate(head) if DESC_HEAD.search(h) and not ADMIN.search(h)
                     and not re.search(r"\b(no\.?|number|code|sl|s\.?\s?no)\s*$", h, re.I)]
            strong_cols = [i for i in cands if re.search(r"descr|name of|nomenclature|particular|details", head[i], re.I)]
            di = (strong_cols or cands or [None])[0]
            if di is None:
                continue
            qi = next((i for i, h in enumerate(head) if i != di and QTY_HEAD.search(h)), None)
            strong = re.search(r"name of (?:the )?(?:item|equipment|goods|material|article|product|instrument)|nomenclature|description of (?:item|goods|material)",
                               head[di], re.I)
            if qi is None and not strong:
                continue                      # a description column without quantities (e.g. a document checklist) is not an item table
            for row in t[1:]:
                if di >= len(row):
                    continue
                desc = _strip_numbering(_clean(row[di]))
                if not _is_item_text(desc):
                    continue
                qty = _clean(row[qi]) if qi is not None and qi < len(row) else None
                if qi is not None and not qty and len(t) > 6:
                    continue                      # empty price-schedule templates
                out.append({"text": desc, "qty": qty or None, "page": p["page"], "source": "table"})
    return out


GEM_QTY = re.compile(r"(?:^|\n)(?:Additional Specification Parameters\s*-\s*)?([A-Z][^\n]{3,220}?)\s*\(\s*([\d,]+)\s*(pieces|nos?|numbers?|sets?|units?|kgs?|kilograms?|meters?|metres?|mtrs?|litres?|liters?|pairs?|packs?|boxes|box|rolls?|reams?|packets?|bottles?|lots?|tonnes?|each|bags?)\s*\)", re.I)
GEM_CAT = re.compile(r"Item Category\s*\n\s*([^\n]{4,300})")


def items_from_gem(pages: List[dict]) -> List[dict]:
    """GeM bid documents: "Item Category <name>" and "<category> ( 223 pieces )" headings of the technical specification."""
    out = []
    for p in pages:
        t = p["text"]
        for m in GEM_QTY.finditer(t):
            name = _clean(re.sub(r"^Additional Specification Parameters\s*-\s*", "", m.group(1), flags=re.I))
            if _is_item_text(name) or re.search(r"\bIS\s*\d", name):
                out.append({"text": name, "qty": f"{m.group(2)} {m.group(3)}", "page": p["page"], "source": "gem"})
        for m in GEM_CAT.finditer(t):
            for part in re.split(r",(?=[A-Z])", m.group(1)):
                name = _clean(re.sub(r"\s*\(Q\d\)\s*$", "", part))
                if len(name) > 3:
                    out.append({"text": name, "qty": None, "page": p["page"], "source": "gem"})
    return out


def items_from_text(pages: List[dict]) -> List[dict]:
    out = []
    for p in pages:
        for m in SUPPLY_RE.finditer(p["text"]):
            desc = _clean(m.group(2))
            desc = re.split(r"\s(?:as per|in accordance with|conforming to|at site|for the office|complete in all respects)\b", desc, 1)[0] \
                if len(desc) > 120 else desc
            if _is_item_text(desc):
                q = UNIT_RE.search(m.group(0))
                out.append({"text": desc, "qty": q.group(0) if q else None, "page": p["page"], "source": "supply-line"})
    return out


def spec_context(pages: List[dict], item_text: str, max_chars: int = 700) -> Optional[str]:
    """Specification lines for an item: text after a technical-specification heading on the page where the item name
    appears (or the first technical-specification section)."""
    key = [w for w in re.findall(r"[a-z]{4,}", item_text.lower())][:3]
    best = None
    for p in pages:
        t = p["text"]
        h = SPEC_HEAD.search(t)
        if not h:
            continue
        seg = t[h.end(): h.end() + 3000]
        if key and all(k in seg.lower() for k in key[:2]):
            best = seg                          # only a specification section that actually talks about this item
            break
    if not best:
        return None
    lines = [l for l in (_clean(x) for x in best.split("\n")) if len(l) > 8 and not ADMIN.search(l)]
    return " ".join(lines)[:max_chars] or None


SERVICE_RE = re.compile(r"\b(hiring|hire|services?|consultan|manpower|outsourc|maintenance contract|amc|cmc|licen[cs]e|subscription|software|"
                        r"insurance|catering|security guards?|housekeeping|transport(?:ation)? services|event|training)\b", re.I)


PURPOSE_RE = re.compile(r"\s+(?:for|at|in|to be used|required for|meant for)\s+(?:the\s+)?(?:construction|use|office|department|hospital|"
                        r"project|building|site|work|ward|campus|school|college|institute|laboratory|lab|centre|center|district|block|premises)\b.*$", re.I)


def split_products(desc: str) -> List[str]:
    """ "Cement and TMT Reinforcement Steel for Construction of G+3 PHC" → ["Cement", "TMT Reinforcement Steel"]."""
    d = PURPOSE_RE.sub("", desc).strip(" ,.")
    parts = [p.strip(" ,.") for p in re.split(r"\s*(?:,|\band\b|&)\s*", d) if p.strip(" ,.")]
    if 2 <= len(parts) <= 4 and all(re.search(r"[A-Za-z]{3,}", p) and len(p.split()) <= 6 for p in parts):
        return parts
    return [d or desc]


def extract_items(pages: List[dict], limit: int = 40) -> List[dict]:
    head = " ".join(p["text"] for p in pages[:2])
    is_gem = bool(re.search(r"Item Category", head) and re.search(r"GEM/\d{4}/[BR]/\d+|Bid Number", head))
    gem = items_from_gem(pages) if is_gem else []
    raw = gem if gem else items_from_tables(pages) + items_from_text(pages)
    items = []
    for it in raw:
        for part in (split_products(it["text"]) if it["source"] not in ("table", "gem") else [it["text"]]):
            if _is_item_text(part) or it["source"] == "gem":
                items.append({**it, "text": part})
    seen, out = {}, []
    for it in items:
        k = re.sub(r"[^a-z0-9]+", " ", re.sub(r"\((?:V|Q)\d+\)", "", it["text"]).lower()).strip()[:80]
        if not k:
            continue
        if k in seen:
            if not seen[k].get("qty") and it.get("qty"):
                seen[k]["qty"] = it["qty"]
            continue
        seen[k] = it
        it["is_service"] = bool(SERVICE_RE.search(it["text"]))
        out.append(it)
    return out[:limit]


PLACE_WORDS = {"auditorium", "hall", "office", "room", "ward", "hospital", "school", "building", "campus", "main", "site", "premises", "block",
               "department", "college", "institute", "laboratory", "lab", "canteen", "hostel", "residential", "quarters", "guest", "house",
               "at", "walking", "ramps", "ramp", "area", "areas", "floor", "ground", "first", "second", "new", "old", "existing", "various"}


def item_query(text: str) -> str:
    """Remove place / purpose words ("Auditorium ceiling light" → "ceiling light") when product words remain."""
    words = re.findall(r"[\w/.\-+]+", text)
    kept = [w for w in words if w.lower() not in PLACE_WORDS]
    return " ".join(kept) if len([w for w in kept if re.search(r"[A-Za-z]{3,}", w)]) >= 1 else text


def item_section(pages: List[dict], item_text: str, max_chars: int = 400) -> Optional[str]:
    """The clauses under a numbered heading that names the item ("3. Cement 3.1 Type: Ordinary Portland Cement 43 Grade …")."""
    keys = [w for w in re.findall(r"[a-z]{4,}", item_text.lower()) if w not in PLACE_WORDS][:2]
    if not keys:
        return None
    rx = re.compile(r"(?:^|\n)\s*\d{1,2}(?:\.\d+)*\.?\s+[^\n]{0,40}\b(" + "|".join(map(re.escape, keys)) + r")\w*\b[^\n]{0,60}\n", re.I)
    for p in pages:
        m = rx.search(p["text"])
        if m:
            seg = p["text"][m.end(): m.end() + 1500]
            nxt = re.search(r"\n\s*\d{1,2}\.\s+[A-Z][A-Za-z ]{2,40}\n", seg)
            seg = seg[: nxt.start()] if nxt else seg
            lines = [_clean(l) for l in seg.split("\n") if len(_clean(l)) > 6 and not ADMIN.search(l)]
            txt = " ".join(lines)[:max_chars]
            if txt:
                return txt
    return None
