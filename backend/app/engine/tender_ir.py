"""
Tender Intermediate Representation (Tender IR).

Turns page-preserving text into a clause tree — the "AST" of a tender — so that every
downstream conclusion can cite  document -> page -> clause -> character span.

    Section "TECHNICAL SPECIFICATIONS"
      Clause 4        heading="Technical Requirements"
        Clause 4.1    text="Bars shall conform to IS 1786:2008 grade Fe 500D ..."
        Clause 4.2    ...
    Annexure II
      Clause AII/1    ...
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from app.engine.docparse import ParsedDocument

CLAUSE_NUM = re.compile(r"^\s*(?:Clause\s+|Cl\.\s*|Section\s+)?(?P<key>\d{1,2}(?:\.\d{1,3}){0,4})(?:[.)]|\s*[:\-–])?\s+(?P<rest>\S.*)$", re.IGNORECASE)
ANNEX = re.compile(r"^\s*(?P<kind>ANNEXURE|ANNEX|APPENDIX|SCHEDULE)\s*[\-–:]?\s*(?P<id>[A-Z0-9IVX]{1,5})?\b\s*[:.\-–]?\s*(?P<rest>.*)$", re.IGNORECASE)
UNIT_START = re.compile(r"^(?:mm|cm|m|kg|mpa|n/mm|%|nos?\.?|days?|months?|sq\.?\s?mm|v|kv|w)\b", re.IGNORECASE)

SECTION_TYPES = [
    ("technical", ["technical specification", "technical requirement", "specification", "scope of supply", "schedule of requirement", "material", "technical particulars"]),
    ("testing", ["testing", "test", "quality assurance", "quality control"]),
    ("inspection", ["inspection", "sampling"]),
    ("acceptance", ["acceptance", "rejection"]),
    ("certification", ["certification", "licence", "license", "bis mark", "isi"]),
    ("delivery", ["delivery", "schedule", "dispatch", "consignee"]),
    ("warranty", ["warranty", "guarantee", "defect liability"]),
    ("eligibility", ["eligibility", "qualification", "pre-qualification", "bidder", "experience", "turnover"]),
    ("commercial", ["payment", "price", "commercial", "penalty", "liquidated damages", "emd", "security"]),
    ("packaging", ["packing", "packaging", "marking"]),
    ("general", ["general", "instructions", "conditions", "introduction", "notice inviting", "nit"]),
]


@dataclass
class Clause:
    key: str
    heading: str
    text: str
    page_start: int
    page_end: int
    doc_name: str
    section: str = ""
    section_type: str = "general"
    parent: Optional[str] = None
    annexure: Optional[str] = None
    tables: List[List[List[str]]] = field(default_factory=list)
    domain_hint: List[str] = field(default_factory=list)   # product domain inherited from the parent heading

    def to_dict(self) -> dict:
        return asdict(self)


def assign_domain_hints(clauses: List["Clause"]) -> None:
    """'3. Technical Specifications — Item 1: LED lamp' → sub-clauses 3.x that never repeat the product name
    ('3.8 Registration: The offered model shall be registered…') still belong to the lighting domain."""
    from app.engine.ontology import detect_domains
    by_key = {c.key: c for c in clauses}
    for c in clauses:
        if detect_domains(c.heading + " " + c.text):
            continue
        p = by_key.get(c.parent) if c.parent else None
        while p is not None:
            d = detect_domains(p.heading)
            if d:
                c.domain_hint = d[:1]
                break
            p = by_key.get(p.parent) if p.parent else None


@dataclass
class TenderIR:
    doc_name: str
    doc_type: str
    title: str
    clauses: List[Clause]
    sections: List[str]
    meta: Dict = field(default_factory=dict)

    def clause_map(self) -> Dict[str, Clause]:
        return {c.key: c for c in self.clauses}

    def to_dict(self) -> dict:
        return {"doc_name": self.doc_name, "doc_type": self.doc_type, "title": self.title,
                "sections": self.sections, "meta": self.meta, "clauses": [c.to_dict() for c in self.clauses]}


def classify_section(text: str) -> str:
    low = (text or "").lower()
    for stype, kws in SECTION_TYPES:
        if any(re.search(r"\b" + re.escape(k) + r"s?\b", low) for k in kws):
            return stype
    return "general"


def detect_doc_type(text: str, filename: str = "") -> str:
    head = (filename + "\n" + (text or "")[:600]).lower()
    if re.search(r"notice inviting tender|\bnit\b|invitation for bids|request for proposal|bid document", head) and not re.search(r"corrigendum|addendum", head):
        return "tender"
    if re.search(r"\bcorrigendum\b|\baddendum\b|\bamendment\s+(?:no|#)", head):
        return "corrigendum"
    if re.search(r"pre[- ]?bid|clarifications? to (?:bidders|queries)|replies to (?:pre-bid )?queries|query\s*no", head):
        return "prebid"
    if re.search(r"\bdatasheet\b|data sheet|technical data|product specification sheet", head):
        return "datasheet"
    if re.search(r"test report|test certificate|nabl|laboratory report", head):
        return "test_report"
    if re.search(r"licen[cs]e|cm/l|certificate of conformity|registration certificate", head):
        return "certificate"
    return "tender"


def _is_heading(line: str) -> bool:
    s = line.strip()
    if len(s) < 4 or len(s) > 90 or s.startswith("|"):
        return False
    letters = re.sub(r"[^A-Za-z]", "", s)
    return len(letters) >= 4 and letters.isupper() and not re.search(r"\d{3,}", s)


def build_ir(doc: ParsedDocument, doc_type: Optional[str] = None) -> TenderIR:
    full_text = doc.text
    dtype = doc_type or detect_doc_type(full_text, doc.filename)
    clauses: List[Clause] = []
    sections: List[str] = []
    title = ""
    current_section = ""
    annex: Optional[str] = None
    cur: Optional[Clause] = None
    preamble_lines: List[str] = []
    seen_keys: Dict[str, int] = {}

    def close():
        nonlocal cur
        if cur is not None:
            cur.text = cur.text.strip()
            clauses.append(cur)
        cur = None

    def unique(key: str) -> str:
        if key not in seen_keys:
            seen_keys[key] = 1
            return key
        seen_keys[key] += 1
        return f"{key}#{seen_keys[key]}"

    for page in doc.pages:
        for raw in page.text.splitlines():
            line = raw.rstrip()
            if not line.strip():
                if cur is not None:
                    cur.text += "\n"
                continue
            if not title and len(line.strip()) > 8 and not CLAUSE_NUM.match(line):
                title = line.strip()[:160]
            am = ANNEX.match(line)
            if am and (am.group("id") or am.group("rest")) and len(line) < 120:
                close()
                annex = (am.group("kind").title() + " " + (am.group("id") or "")).strip()
                current_section = f"{annex}: {am.group('rest').strip()}".strip(": ")
                sections.append(current_section)
                cur = Clause(key=unique(annex.replace(" ", "-")), heading=am.group("rest").strip() or annex,
                             text="", page_start=page.page_no, page_end=page.page_no, doc_name=doc.filename,
                             section=current_section, section_type=classify_section(current_section), annexure=annex)
                continue
            cm = CLAUSE_NUM.match(line)
            if cm and not UNIT_START.match(cm.group("rest")) and (cm.group("rest")[0].isupper() or cm.group("rest")[0] in "(\"'"):
                close()
                key = cm.group("key")
                if annex:
                    key = f"{annex.replace(' ', '-')}/{key}"
                rest = cm.group("rest").strip()
                heading, body, explicit = rest, "", True
                # "4.1 Material: Bars shall ..." -> heading "Material"
                hm = re.match(r"^([A-Z][A-Za-z /&()\-]{2,60}?)\s*[:\-–]\s+(.*)$", rest)
                if hm:
                    heading, body = hm.group(1).strip(), hm.group(2)
                elif len(rest) > 70 or rest.endswith("."):
                    heading, body, explicit = rest[:60], rest, False
                parent = None
                last = key.split("/")[-1]
                if "." in last:
                    parent = key.rsplit(".", 1)[0]
                parent_clause = next((c for c in reversed(clauses) if c.key == parent), None) if parent else None
                stype = classify_section(heading) if explicit else "general"
                if stype == "general" and parent_clause is not None:
                    stype = parent_clause.section_type
                if stype == "general":
                    stype = classify_section(current_section)
                if stype == "general" and not explicit:
                    stype = classify_section(body)
                cur = Clause(key=unique(key), heading=heading, text=body, page_start=page.page_no,
                             page_end=page.page_no, doc_name=doc.filename, section=current_section,
                             section_type=stype, parent=parent, annexure=annex)
                continue
            if _is_heading(line):
                close()
                current_section = line.strip().title()
                sections.append(current_section)
                continue
            if cur is None:
                preamble_lines.append(line.strip())
            else:
                cur.text += ("\n" if cur.text and not cur.text.endswith("\n") else "") + line.strip()
                cur.page_end = page.page_no
                if line.strip().startswith("|"):
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                        if not cur.tables:
                            cur.tables.append([])
                        cur.tables[-1].append(cells)
    close()


    if not clauses:
        # unstructured input (e.g. a pasted paragraph) -> one synthetic clause per paragraph
        paras = [p.strip() for p in re.split(r"\n\s*\n", "\n".join(pl for pl in preamble_lines)) if p.strip()]
        if not paras:
            paras = [doc.text.strip()]
        for i, p in enumerate(paras, 1):
            clauses.append(Clause(key=f"P{i}", heading=p[:60], text=p, page_start=doc.pages[0].page_no if doc.pages else 1,
                                  page_end=doc.pages[-1].page_no if doc.pages else 1, doc_name=doc.filename,
                                  section="Specification", section_type=classify_section(p) if len(paras) > 1 else "technical"))
    assign_domain_hints(clauses)
    return TenderIR(doc_name=doc.filename, doc_type=dtype, title=title or doc.filename, clauses=clauses,
                    sections=sections, meta={**doc.meta(), "preamble": "\n".join(preamble_lines)[:2000]})
