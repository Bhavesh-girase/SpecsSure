"""
Evidence extraction from bidder documents (datasheets, BIS licence data, test reports).

Every extracted fact keeps document → page → snippet so the compliance matrix can show the exact
line an evaluator should look at. Evidence strength is graded:
    3 = accredited laboratory test report   2 = certification/licence record   1 = manufacturer claim (datasheet)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Dict, List, Optional

from app.engine import ontology, units
from app.engine.docparse import ParsedDocument
from app.engine.std_refs import parse_citations
from app.engine.tender_ir import detect_doc_type

STRENGTH = {"test_report": 3, "certificate": 2, "datasheet": 1, "other": 1}
DATE = re.compile(r"(\d{1,2})[./\-](\d{1,2})[./\-](20\d{2})")


@dataclass
class EvidenceItem:
    doc_name: str
    doc_type: str
    page: int
    kind: str                         # parameter | sizes | standard | licence | lab | declaration
    snippet: str
    strength: int
    parameter: Optional[str] = None
    parameter_label: Optional[str] = None
    value: Optional[float] = None
    values: List[float] = field(default_factory=list)
    unit: Optional[str] = None
    raw_value: Optional[str] = None
    qualifier: Optional[str] = None   # min | max | typical | result
    method: Optional[str] = None
    extra: Dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def _d(m) -> Optional[str]:
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except Exception:
        return None


def extract_evidence(doc: ParsedDocument, doc_type: Optional[str] = None, domains: Optional[List[str]] = None) -> Dict:
    dtype = doc_type or detect_doc_type(doc.text, doc.filename)
    if dtype not in STRENGTH:
        dtype = "other"
    strength = STRENGTH[dtype]
    doms = domains or ontology.detect_domains(doc.text) or None
    items: List[EvidenceItem] = []
    meta: Dict = {"doc_type": dtype, "doc_name": doc.filename, "sha256": doc.sha256, "domains": (doms or [])[:1],
                  "pages": doc.page_count, "parser": doc.parser}

    STOP_LABELS = re.compile(r"^(?:grade|status|product|standard|conforming to|licensee|licen[cs]e no\.?|sizes?(?: covered| available)?|"
                             r"valid (?:up ?to|till)|sample|customer|report no\.?|date(?: of report)?|laboratory|accreditation|remarks)$", re.I)
    for page in doc.pages:
        header_q = None
        for raw in page.text.splitlines():
            line = raw.strip()
            if not line:
                continue
            # ---- licence / certificate / lab facts (metadata, never 'continue')
            lm = re.search(r"\b(CM/L[-\s]?\d{7,10}|R-\d{8})\b", line)
            if lm:
                meta["licence_no"] = lm.group(1)
                items.append(EvidenceItem(doc.filename, dtype, page.page_no, "licence", line, strength, raw_value=lm.group(1)))
            vm = re.search(r"valid\s*(?:up\s*to|till|until|upto)\s*[:\-]?\s*" + DATE.pattern, line, re.I)
            if vm:
                meta["valid_to"] = date(int(vm.group(3)), int(vm.group(2)), int(vm.group(1))).isoformat()
            if re.search(r"^licensee\s*[:\-]", line, re.I):
                meta["licensee"] = line.split(":", 1)[1].strip()
            gm = re.search(r"^grade\s*[:\-]\s*(.+)$", line, re.I)
            if gm:
                meta["grade"] = gm.group(1).strip()
            if re.search(r"^status\s*[:\-]", line, re.I):
                meta["status"] = line.split(":", 1)[1].strip()
            if re.search(r"^(?:laboratory|lab|testing (?:centre|center))\s*[:\-]", line, re.I):
                meta["lab"] = re.split(r"\s+(?:NABL|Accreditation|Certificate|Report)\b", line.split(":", 1)[1].strip(), 1)[0].strip(" ,;|")
            nm = re.search(r"(?<![A-Z0-9])(TC-[A-Z0-9\-]+)\b", line)
            if nm and re.search(r"NABL|accredit|17025", line, re.I):
                meta["nabl_certificate"] = nm.group(1)
                meta["accredited"] = True
            rm = re.search(r"report\s*no\.?\s*[:\-]\s*(\S+?)(?=Date\b|\s|$)", line, re.I)
            if rm:
                meta["report_no"] = rm.group(1).rstrip(",;|")
            dm = re.search(r"(?:date of (?:report|issue|test)|report date|(?<![A-Za-z])date)\s*[:\-]\s*" + DATE.pattern, line, re.I)
            if dm:
                meta["report_date"] = date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1))).isoformat()
            if re.search(r"not tested|was not tested|not carried out", line, re.I):
                meta.setdefault("not_tested", []).append(line)
                for pid, _, _ in ontology.find_parameters(line, doms):
                    meta.setdefault("not_tested_parameters", []).append(pid)
            # ---- size lists
            sm = re.search(r"(?:sizes?|diameters?)\s*(?:available|offered|covered)?\s*[:\-]\s*(.+)$", line, re.I)
            if sm:
                rng = re.search(r"(\d+)\s*mm\s*to\s*(\d+)\s*mm", sm.group(1), re.I)
                if rng:
                    lo, hi = float(rng.group(1)), float(rng.group(2))
                    vals = [s for s in [6, 8, 10, 12, 16, 20, 25, 28, 32, 36, 40] if lo <= s <= hi]
                else:
                    vals = [units.parse_number(x) for x in re.findall(r"\d+(?:\.\d+)?", sm.group(1))]
                items.append(EvidenceItem(doc.filename, dtype, page.page_no, "sizes", line, strength, "nominal_diameter",
                                          "Nominal Diameter", values=[v for v in vals if v is not None], unit="mm"))
                continue
            # ---- key/value from table rows or "Label : value" lines
            label, value, method = None, None, None
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2 and not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    if not re.search(r"\d", " ".join(cells[1:2])):
                        hdr = " ".join(cells).lower()
                        header_q = "max" if "maximum" in hdr else ("min" if "minimum" in hdr else header_q)
                        continue
                    label, value = cells[0], cells[1]
                    method = cells[2] if len(cells) > 2 else None
            else:
                m = re.match(r"^([A-Za-z0-9%+/().\- ]{3,60}?)\s*[:–-]\s+(.+)$", line)
                if m:
                    label, value = m.group(1), m.group(2)
            if label and value and not STOP_LABELS.match(label.strip()):
                params = ontology.find_parameters(label, doms)
                masked_value = value
                for ref in parse_citations(value):
                    masked_value = masked_value.replace(ref.raw, " " * len(ref.raw))
                num = re.search(rf"({units.NUMBER_REGEX})\s*({units.UNIT_REGEX})?", masked_value, re.I)
                if params and num:
                    pid = params[0][0]
                    v = units.parse_number(num.group(1))
                    conv = units.convert(v, num.group(2), ontology.param_unit(pid)) if v is not None else None
                    q = "min" if re.search(r"\bmin", value, re.I) else ("max" if re.search(r"\bmax", value + " " + label, re.I) else
                                                                         (header_q or ("result" if dtype == "test_report" else "typical")))
                    items.append(EvidenceItem(doc.filename, dtype, page.page_no, "parameter", line, strength, pid,
                                              ontology.param_label(pid), round(conv.value, 6) if conv else v, None,
                                              ontology.param_unit(pid), value, q, method))
                    continue
            # ---- standards claimed
            for ref in parse_citations(line):
                if ref.body == "BIS" and re.search(r"conform|standard|is no|as per|specification|comply", line, re.I):
                    items.append(EvidenceItem(doc.filename, dtype, page.page_no, "standard", line, strength,
                                              raw_value=ref.display, extra={"family": ref.family, "year": ref.year}))
    for ref in parse_citations(doc.text):
        if ref.body == "BIS" and not any(i.kind == "standard" and i.extra.get("family") == ref.family for i in items):
            if dtype == "certificate":
                items.append(EvidenceItem(doc.filename, dtype, 1, "standard", ref.raw, strength, raw_value=ref.display,
                                          extra={"family": ref.family, "year": ref.year}))
    return {"meta": meta, "items": [i.to_dict() for i in items]}
