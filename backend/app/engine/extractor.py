"""
Deterministic requirement extraction: Tender IR clause -> typed, normalised, span-anchored requirements.

Each requirement records *exactly* where it came from (clause, page, character span) so that
explanations can quote the source verbatim. An optional LLM pass can add requirements, but only
if its quoted evidence is found verbatim in the clause (grounded-quote verification, see guardrails).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from app.engine import ontology, units
from app.engine.std_refs import parse_citations, find_generic_references
from app.engine.tender_ir import Clause, TenderIR

NUM = units.NUMBER_REGEX
U = units.UNIT_REGEX

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
                "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty five": 45,
                "forty-five": 45, "forty": 40, "sixty": 60, "ninety": 90, "hundred": 100}

KIND_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("brand", re.compile(r"\b(?:brand|make|makes)\b", re.I)),
    ("certification", re.compile(r"\bISI\b|\bBIS\b[^.]{0,40}\blicen[cs]e|\bCM/L\b|\bCRS\b|\bcertif(?:ied|ication)\b|\bstandard mark\b|\blicen[cs]e\b", re.I)),
    ("testing", re.compile(r"\btest(?:ed|ing|s)?\b|\bNABL\b|\blaborator(?:y|ies)\b", re.I)),
    ("inspection", re.compile(r"\binspect(?:ion|ed)?\b|third[- ]party|pre-dispatch", re.I)),
    ("acceptance", re.compile(r"\baccept(?:ance|ed)\b|\breject(?:ion|ed)?\b|\bsampling\b|\bAQL\b", re.I)),
    ("delivery", re.compile(r"\bdeliver(?:y|ed)?\b|\bdispatch(?:ed)?\b", re.I)),
    ("warranty", re.compile(r"\bwarrant(?:y|ee)\b|\bguarantee\b|\bdefect(?:ive)?\b", re.I)),
    ("packaging", re.compile(r"\bpack(?:ed|ing|aged)\b|\bmarking\b|\bbags?\b", re.I)),
    ("eligibility", re.compile(r"\bbidders? (?:shall|must|should) (?:have|possess)\b|\bturnover\b|\bexperience\b|\bsimilar works?\b", re.I)),
    ("documentation", re.compile(r"\bsubmit(?:ted)?\b|\bdocuments?\b|\bcertificates?\b", re.I)),
]
MODALITY = re.compile(r"\b(shall|must|should|may|will|is required to|are required to|preferably)\b", re.I)
DATE_RX = re.compile(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](20\d{2})\b|\b(20\d{2})-(\d{2})-(\d{2})\b")
STEEL_GRADE = re.compile(r"\bFe\s?(\d{3})\s?(D|S)?\b", re.I)
CEMENT_GRADE = re.compile(r"\b(33|43|53)[\s-]*grade\b|\bgrade\s*(33|43|53)\b", re.I)
IP_CODE = re.compile(r"\bIP\s?([0-6])([0-9])\b")


@dataclass
class Requirement:
    id: str
    clause_key: str
    doc_name: str
    page: int
    kind: str
    text: str
    span: Tuple[int, int]
    tags: List[str] = field(default_factory=list)
    parameter: Optional[str] = None
    parameter_label: Optional[str] = None
    domain: Optional[str] = None
    op: Optional[str] = None                 # min | max | range | eq | enum
    value: Optional[float] = None
    value_max: Optional[float] = None
    values: List[float] = field(default_factory=list)
    unit_raw: Optional[str] = None
    norm: Dict = field(default_factory=dict)  # {min, max, values, unit}
    tolerance: Optional[Dict] = None
    standards: List[Dict] = field(default_factory=list)
    grade: Optional[str] = None
    modality: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    date_value: Optional[str] = None
    confidence: float = 0.9
    method: str = "rule"
    matched_text: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["span"] = list(self.span)
        return d

    @property
    def bounds(self) -> Tuple[Optional[float], Optional[float]]:
        return self.norm.get("min"), self.norm.get("max")


def _replace_number_words(s: str) -> str:
    def rep(m):
        return str(NUMBER_WORDS[m.group(0).lower()])
    rx = re.compile(r"\b(" + "|".join(sorted(map(re.escape, NUMBER_WORDS), key=len, reverse=True)) + r")\b", re.I)
    return rx.sub(rep, s)


def _mask_citations(s: str) -> str:
    """Replace standard citations & dates with spaces so '1786-2008' is not read as a range."""
    out = list(s)
    for r in parse_citations(s):
        end = r.end
        # IEC-style part suffix and edition that the family regex leaves behind: "IS/IEC 60898-1:2002", "61730-2"
        m = re.match(r"(?:\s*-\s*\d+){1,3}(?:\s*:\s*\d{4})?", s[end:])
        if m:
            end += m.end()
        for i in range(r.start, min(end, len(out))):
            out[i] = " "
    for m in DATE_RX.finditer(s):
        for i in range(m.start(), m.end()):
            out[i] = " "
    for m in re.finditer(r"\bFe\s?\d{3}\s?[DS]?\b|\bIP\s?\d{2}\b|\b\d+\s*(?:grade|Grade)\b|\bGrade\s*\d+\b|\bPart\s*\d+\b|\bZone\s*[IVX\d]+\b|\bNo\.\s*\S+", s):
        for i in range(m.start(), m.end()):
            out[i] = " "
    return "".join(out)


_PATTERNS = [
    ("range", re.compile(rf"between\s+(?P<a>{NUM})\s*(?P<ua>{U})?\s+(?:and|to)\s+(?P<b>{NUM})\s*(?P<ub>{U})?", re.I)),
    ("range", re.compile(rf"(?P<a>{NUM})\s*(?P<ua>{U})?\s*(?:–|-|to)\s*(?P<b>{NUM})\s*(?P<ub>{U})", re.I)),
    ("tol", re.compile(rf"(?P<a>{NUM})\s*(?P<ua>{U})?\s*(?:±|\+/-|\+-|\+/−)\s*(?P<t>{NUM})\s*(?P<ut>%|{U})?", re.I)),
    ("tol", re.compile(rf"(?P<a>{NUM})\s*(?P<ua>{U})?\s*,?\s*(?:with\s+)?(?:a\s+)?tolerance\s+of\s*(?:±|\+/-|\+-|plus\s+or\s+minus)\s*(?P<t>{NUM})\s*(?P<ut>%|{U})?", re.I)),
    ("tol2", re.compile(rf"(?P<a>{NUM})\s*(?P<ua>{U})?\s*\(\s*\+\s*(?P<p>{NUM})\s*/\s*[-−]\s*(?P<m>{NUM})\s*\)", re.I)),
    ("min", re.compile(rf"(?:not\s+(?:be\s+)?less\s+than|no\s+less\s+than|minimum(?:\s+of)?|min\.?|at\s+least|≥|>=|greater\s+than(?:\s+or\s+equal\s+to)?|more\s+than|above|in\s+excess\s+of)\s*(?:of\s+)?(?P<a>{NUM})\s*(?P<ua>{U})?", re.I)),
    ("max", re.compile(rf"(?:not\s+(?:be\s+)?more\s+than|no\s+more\s+than|(?:shall\s+)?not\s+exceed(?:ing)?|maximum(?:\s+of)?|max\.?|up\s?to|≤|<=|less\s+than|below|within|under)\s*(?:of\s+)?(?P<a>{NUM})\s*(?P<ua>{U})?", re.I)),
    ("sfx", re.compile(rf"(?P<a>{NUM})\s*(?P<ua>{U})?\s*\(?\s*(?P<d>min(?:imum)?|max(?:imum)?)\b\.?\)?", re.I)),
    ("enum", re.compile(rf"(?P<list>{NUM}\s*(?:{U})?(?:\s*(?:,|and|or|&)\s*{NUM}\s*(?:{U})?)+)", re.I)),
    ("eq", re.compile(rf"(?:shall\s+be|should\s+be|is|of|=|:)\s*(?P<a>{NUM})\s*(?P<ua>{U})?", re.I)),
    ("bare", re.compile(rf"(?P<a>{NUM})\s*(?P<ua>{U})?", re.I)),
]


def parse_constraint(segment: str) -> Optional[dict]:
    """Find the first (left-most, most specific) quantitative constraint in a text segment."""
    best = None
    for kind, rx in _PATTERNS:
        m = rx.search(segment)
        if not m:
            continue
        cand = (m.start(), -len(m.group(0)), kind, m)
        if kind == "bare" and best is not None:
            continue
        if best is None or cand[:2] < best[:2]:
            best = cand
    if best is None:
        return None
    _, _, kind, m = best
    if kind in ("eq", "bare"):
        num_pos = m.start("a")
        upgraded = False
        for k2, rx2 in _PATTERNS:
            if k2 in ("range", "tol", "tol2"):
                m2 = rx2.search(segment)
                if m2 and m2.start() == num_pos:
                    kind, m, upgraded = ("range" if k2 == "range" else k2), m2, True
                    break
        if not upgraded:
            em = next(rx for k3, rx in _PATTERNS if k3 == "enum").search(segment)
            if em and em.start() - m.start() <= 6:
                kind, m = "enum", em
    g = m.groupdict()
    if kind == "range":
        a, b = units.parse_number(g["a"]), units.parse_number(g["b"])
        if a is None or b is None or a > b:
            return None
        return {"op": "range", "value": a, "value_max": b, "unit": g.get("ub") or g.get("ua"), "match": m.group(0), "start": m.start()}
    if kind == "tol":
        a, t = units.parse_number(g["a"]), units.parse_number(g["t"])
        rel = g.get("ut") == "%"
        tol = a * t / 100 if rel else t
        return {"op": "range", "value": a - tol, "value_max": a + tol, "unit": g.get("ua"),
                "tolerance": {"nominal": a, "plus": tol, "minus": tol, "relative_percent": t if rel else None},
                "match": m.group(0), "start": m.start()}
    if kind == "tol2":
        a, p, mi = units.parse_number(g["a"]), units.parse_number(g["p"]), units.parse_number(g["m"])
        return {"op": "range", "value": a - mi, "value_max": a + p, "unit": g.get("ua"),
                "tolerance": {"nominal": a, "plus": p, "minus": mi}, "match": m.group(0), "start": m.start()}
    if kind in ("min", "max"):
        return {"op": kind, "value": units.parse_number(g["a"]), "unit": g.get("ua"), "match": m.group(0), "start": m.start()}
    if kind == "sfx":
        return {"op": "min" if g["d"].lower().startswith("min") else "max", "value": units.parse_number(g["a"]),
                "unit": g.get("ua"), "match": m.group(0), "start": m.start()}
    if kind == "enum":
        items = re.findall(rf"({NUM})\s*({U})?", g["list"], re.I)
        vals = [units.parse_number(v) for v, _ in items]
        unit = next((u for _, u in reversed(items) if u), None)
        return {"op": "enum", "values": [v for v in vals if v is not None], "unit": unit, "match": m.group(0), "start": m.start()}
    return {"op": "eq", "value": units.parse_number(g["a"]), "unit": g.get("ua"), "match": m.group(0), "start": m.start(),
            "weak": kind == "bare"}


def split_sentences(text: str) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    pos = 0
    for line in text.split("\n"):
        line_start = text.find(line, pos)
        pos = line_start + len(line)
        if not line.strip():
            continue
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            joined = cells[0] + ": " + " ".join(cells[1:]) if len(cells) > 1 else cells[0]
            out.append((joined, line_start))
            continue
        cut = 0
        for m in re.finditer(r"(?<=[.;])\s+(?=[A-Z(\"'])|(?<=;)\s*", line):
            seg = line[cut:m.start()]
            if seg.strip():
                out.append((seg.strip(), line_start + cut + (len(seg) - len(seg.lstrip()))))
            cut = m.end()
        seg = line[cut:]
        if seg.strip():
            out.append((seg.strip(), line_start + cut + (len(seg) - len(seg.lstrip()))))
    # merge fragments created by abbreviations such as "No." or "Cl."
    merged: List[Tuple[str, int]] = []
    for s, st in out:
        if merged and (re.search(r"\b(?:No|Cl|Rs|viz|e\.g|i\.e|approx|Min|Max)\.$", merged[-1][0]) or len(s) < 4):
            merged[-1] = (merged[-1][0] + " " + s, merged[-1][1])
        else:
            merged.append((s, st))
    return merged


def _parse_date(s: str) -> Optional[date]:
    m = DATE_RX.search(s)
    if not m:
        return None
    try:
        if m.group(3):
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        return date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
    except ValueError:
        return None


def extract_clause(clause: Clause, tender_domains: List[str], counter: Dict[str, int]) -> List[Requirement]:
    reqs: List[Requirement] = []
    own_domains = ontology.detect_domains(clause.heading + " " + clause.text) or list(getattr(clause, "domain_hint", []) or [])
    local_domains = own_domains or tender_domains
    body = clause.text or ""
    for sentence, start in split_sentences(body):
        s_norm = _replace_number_words(sentence)
        masked = _mask_citations(s_norm)
        cites = [r.to_dict() for r in parse_citations(sentence)]
        modality_m = MODALITY.search(sentence)
        modality = modality_m.group(1).lower() if modality_m else None
        tags = [k for k, rx in KIND_PATTERNS if rx.search(sentence)]
        grade = None
        gm = STEEL_GRADE.search(sentence)
        if gm:
            grade = f"Fe {gm.group(1)}{(gm.group(2) or '').upper()}"
        cg = CEMENT_GRADE.search(sentence)
        if cg and not grade:
            grade = cg.group(1) or cg.group(2)

        def new_id() -> str:
            counter[clause.key] = counter.get(clause.key, 0) + 1
            return f"R-{clause.key}-{counter[clause.key]}"

        base = dict(clause_key=clause.key, doc_name=clause.doc_name, page=clause.page_start,
                    text=sentence, span=(start, start + len(sentence)), modality=modality, standards=cites, grade=grade)

        # --- parameter constraints -------------------------------------------------------
        params = ontology.find_parameters(masked, local_domains)
        # section-driven fallbacks (delivery / warranty clauses often omit the noun)
        if not params and clause.section_type in ("delivery", "warranty") and re.search(r"\b\d+\s*(?:days?|weeks?|months?|years?)\b", s_norm, re.I):
            params = [("delivery_period" if clause.section_type == "delivery" else "warranty_period", 0, 0)]
        ip = IP_CODE.search(sentence)
        param_reqs: List[Requirement] = []
        for idx, (pid, ps, pe) in enumerate(params):
            nxt = params[idx + 1][1] if idx + 1 < len(params) else len(masked)
            seg = masked[pe:nxt] if pe else masked
            c = None
            if pid == "ip_rating" and ip:
                c = {"op": "min", "value": float(ip.group(1) + ip.group(2)), "unit": None, "match": ip.group(0), "start": 0}
            else:
                c = parse_constraint(seg)
            if c is None:
                continue
            canonical = ontology.param_unit(pid)
            flags: List[str] = []
            if c.get("weak"):
                flags.append("weak_value_parse")
            unit_raw = c.get("unit")
            if canonical in ("dimensionless",):
                unit_raw = None
            if pid == "bag_mass" and not unit_raw:
                continue
            norm: Dict = {"unit": canonical}
            conv_ok = True

            def cv(v):
                nonlocal conv_ok
                if v is None:
                    return None
                r = units.convert(v, unit_raw, canonical)
                if r is None:
                    conv_ok = False
                    return v
                return round(r.value, 6)

            if c["op"] == "enum":
                norm["values"] = [cv(v) for v in c["values"]]
                norm["min"], norm["max"] = min(norm["values"]), max(norm["values"])
            elif c["op"] == "range":
                norm["min"], norm["max"] = cv(c["value"]), cv(c["value_max"])
            elif c["op"] == "min":
                norm["min"] = cv(c["value"])
            elif c["op"] == "max":
                norm["max"] = cv(c["value"])
            else:
                v = cv(c["value"])
                norm["min"] = norm["max"] = v
            if not unit_raw and canonical not in ("dimensionless", "percent"):
                flags.append("no_unit")
            if not conv_ok:
                flags.append("unit_incompatible")
            if unit_raw and units.is_non_si(unit_raw):
                flags.append("non_si_unit")
            pdef = ontology.parameters()[pid]
            if pdef.get("needs_tolerance") and c["op"] in ("eq", "enum") and not c.get("tolerance") \
                    and not (re.search(r"toleranc", sentence, re.I) and cites):   # "... with tolerances as per IS 1786"
                flags.append("no_tolerance")
            if pid == "warranty_period" and c["op"] == "max":
                c["op"] = "min"
                norm = {"unit": canonical, "min": norm.get("max")}
            if pid in ("delivery_period", "warranty_period") and not re.search(r"\b(?:from|of|after)\b", sentence, re.I):
                flags.append("relative_date_without_anchor")
            dom = next((d for d in local_domains if d in pdef.get("domains", [])), (pdef.get("domains") or ["general"])[0])
            if dom == "general" and len(own_domains) == 1:
                # item-specific warranty / delivery in a multi-item tender ("Warranty — LED lamp: 24 months")
                dom = own_domains[0]
            param_reqs.append(Requirement(
                id=new_id(), kind="parameter", tags=sorted(set(tags + [pdef["category"]])), parameter=pid,
                parameter_label=pdef["label"], domain=dom, op=c["op"], value=c.get("value"), value_max=c.get("value_max"),
                values=c.get("values", []), unit_raw=unit_raw, norm=norm, tolerance=c.get("tolerance"), flags=flags,
                matched_text=c.get("match"), confidence=0.75 if c.get("weak") else 0.93, **base))
        reqs.extend(param_reqs)

        # --- dates ---------------------------------------------------------------------------
        d = _parse_date(sentence)
        if d and not param_reqs:
            reqs.append(Requirement(id=new_id(), kind="schedule", tags=tags, date_value=d.isoformat(),
                                    parameter_label=clause.heading, **base))
            continue

        # --- clause-level obligations (testing / certification / inspection / ...) ----------
        if not param_reqs and (modality or cites or tags):
            primary = None
            if cites and re.search(r"conform|as per|comply|accordance|confirming", sentence, re.I):
                primary = "standard_compliance"
            for k in [t for t in tags if t != "documentation"] + (["documentation"] if "documentation" in tags else []):
                if primary is None:
                    primary = k
            primary = primary or ("standard_compliance" if cites else "general")
            flags = []
            if find_generic_references(sentence):
                flags.append("generic_standard_reference")
            reqs.append(Requirement(id=new_id(), kind=primary, tags=sorted(set(tags)), flags=flags,
                                    parameter_label=clause.heading, **base))
    # attach grade/standards from clause context to parameter requirements lacking them
    clause_cites = [r.to_dict() for r in parse_citations(body)]
    clause_grade = None
    gm = STEEL_GRADE.search(body)
    if gm:
        clause_grade = f"Fe {gm.group(1)}{(gm.group(2) or '').upper()}"
    for r in reqs:
        if r.kind == "parameter":
            if not r.standards:
                r.standards = clause_cites
            if not r.grade:
                r.grade = clause_grade
    return reqs


@dataclass
class ExtractionResult:
    requirements: List[Requirement]
    domains: List[str]
    dates: Dict[str, str]
    grades: Dict[str, str]
    citations: List[Dict]

    def to_dict(self):
        return {"requirements": [r.to_dict() for r in self.requirements], "domains": self.domains,
                "dates": self.dates, "grades": self.grades, "citations": self.citations}


DATE_ROLES = [
    ("publication", r"publication|published|issue of (?:nit|tender)"),
    ("bid_due", r"last date|bid submission|closing date|due date"),
    ("bid_opening", r"opening"),
    ("prebid", r"pre[- ]?bid"),
]


def extract(ir: TenderIR) -> ExtractionResult:
    all_text = " ".join(c.heading + " " + c.text for c in ir.clauses)
    domains = ontology.detect_domains(all_text)
    counter: Dict[str, int] = {}
    reqs: List[Requirement] = []
    for c in ir.clauses:
        reqs.extend(extract_clause(c, domains, counter))
    # tender-level facts
    dates: Dict[str, str] = {}
    for r in reqs:
        if r.kind == "schedule" and r.date_value:
            label = (r.parameter_label or "") + " " + r.text
            for role, rx in DATE_ROLES:
                if re.search(rx, label, re.I) and role not in dates:
                    dates[role] = r.date_value
                    r.tags = sorted(set(r.tags + [f"date:{role}"]))
                    break
    grades: Dict[str, str] = {}
    for r in reqs:
        if r.grade and r.domain and r.domain not in grades:
            grades[r.domain] = r.grade
    for c in ir.clauses:
        low = (c.heading + " " + c.text).lower()
        g = STEEL_GRADE.search(c.text)
        if g and "steel" not in grades:
            grades["steel"] = f"Fe {g.group(1)}{(g.group(2) or '').upper()}"
        cg = CEMENT_GRADE.search(c.text)
        if cg and "cement" not in grades and "cement" in low:
            grades["cement"] = cg.group(1) or cg.group(2)
    cites = []
    seen = set()
    for c in ir.clauses:
        for ref in parse_citations(c.text):
            k = (ref.family, ref.year, c.key)
            if k in seen:
                continue
            seen.add(k)
            d = ref.to_dict()
            d["clause_key"] = c.key
            d["page"] = c.page_start
            cites.append(d)
    return ExtractionResult(reqs, domains, dates, grades, cites)
