"""
Tender Linter — "ESLint for tenders".

A registry of deterministic, individually-testable rules. Every rule has a stable ID, a category,
a default severity, a rationale (with the GFR / BIS basis where one exists) and — where safe — an
*autofix* that can be turned into a draft corrigendum. Findings are fingerprinted so their review
status survives re-compilation (exactly like code-scanning alerts), and exported as SARIF 2.1.0.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional

from app.engine import ontology
from app.engine.context import CompileContext
from app.engine.extractor import Requirement
from app.engine.std_refs import find_generic_references, parse_citations

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}
GFR_144 = "GFR 2017 Rule 144(i): specifications should be objective, functional, generic and measurable and should not indicate a particular trademark, trade name or brand."
GFR_144_III = "GFR 2017 Rule 144(iii): specifications shall, to the extent practicable, be based on national technical regulations or recognised national standards."


@dataclass
class Finding:
    rule_id: str
    rule_name: str
    category: str
    severity: str
    message: str
    clause_key: Optional[str] = None
    page: Optional[int] = None
    doc_name: Optional[str] = None
    quote: Optional[str] = None
    span: Optional[List[int]] = None
    suggestion: Optional[str] = None
    fix: Optional[Dict] = None
    evidence: List[Dict] = field(default_factory=list)
    requirement_ids: List[str] = field(default_factory=list)
    source: str = "deterministic"
    confidence: float = 0.95
    basis: Optional[str] = None
    fingerprint: str = ""

    def finalize(self) -> "Finding":
        anchor = ",".join(sorted(self.requirement_ids)) if self.requirement_ids else (self.quote or self.message)[:120]
        raw = f"{self.rule_id}|{self.clause_key}|{anchor}"
        self.fingerprint = hashlib.sha1(raw.encode()).hexdigest()[:16]
        return self

    def to_dict(self):
        return asdict(self)


@dataclass
class Rule:
    id: str
    name: str
    category: str
    severity: str
    description: str
    basis: Optional[str]
    fn: Callable[[CompileContext], List[Finding]]


RULES: List[Rule] = []


def rule(id: str, name: str, category: str, severity: str, description: str, basis: Optional[str] = None):
    def deco(fn):
        RULES.append(Rule(id, name, category, severity, description, basis, fn))
        return fn
    return deco


def _f(ctx: CompileContext, r: Rule, message: str, clause_key: Optional[str], **kw) -> Finding:
    c = ctx.clause(clause_key)
    return Finding(rule_id=r.id, rule_name=r.name, category=r.category, severity=kw.pop("severity", r.severity),
                   message=message, clause_key=clause_key, page=c.page_start if c else kw.pop("page", None),
                   doc_name=c.doc_name if c else None, basis=kw.pop("basis", r.basis), **kw)


def _rule(rid: str) -> Rule:
    return next(r for r in RULES if r.id == rid)


def _std_url(num: str) -> str:
    return "https://standards.bis.gov.in/"


# =============================================================================================
# Ambiguity & measurability
# =============================================================================================
VAGUE = [
    (r"\b(high|good|best|superior|excellent|first[- ]class|premium) quality\b", "major"),
    (r"\b(durable|long[- ]lasting|heavy[- ]duty|robust|sturdy)\b", "minor"),
    (r"\b(weather[- ]?(?:proof|resistant)|all[- ]weather)\b", "minor"),
    (r"\b(corrosion[- ]resistant|rust[- ](?:free|proof|resistant))\b", "minor"),
    (r"\b(good|fine|smooth|proper) finish\b", "minor"),
    (r"\b(adequate|sufficient|suitable) (?:strength|capacity|thickness|size)\b", "major"),
    (r"\b(reputed|reputable|standard|leading|renowned) (?:brand|make|manufacturer|company)s?\b", "major"),
    (r"\b(state[- ]of[- ]the[- ]art|latest technology|modern)\b", "minor"),
]


@rule("SS-AMB-001", "Vague qualitative term", "ambiguity", "minor",
      "Qualitative adjectives cannot be evaluated objectively and invite disputes at technical evaluation.", GFR_144)
def r_vague(ctx):
    out = []
    r = _rule("SS-AMB-001")
    for c in ctx.clauses:
        for rx, sev in VAGUE:
            for m in re.finditer(rx, c.text, re.I):
                term = m.group(0)
                repl = _vague_replacement(term, c)
                out.append(_f(ctx, r, f"Vague term “{term}” in Clause {c.key} is not measurable.", c.key, severity=sev,
                              quote=term, span=[m.start(), m.end()],
                              suggestion=repl or "Replace with a measurable acceptance criterion (value, unit, test method) or delete.",
                              fix={"op": "replace", "clause_key": c.key, "find": term, "replace": ""} if sev == "minor" else None))
    return out


def _vague_replacement(term: str, c) -> Optional[str]:
    t = term.lower()
    if "durab" in t or "lasting" in t:
        return "Define durability through a measurable test (e.g. accelerated ageing / salt-spray hours / cycles) as per the governing IS, or delete."
    if "quality" in t:
        return "Delete the adjective — quality is already defined by conformity to the cited Indian Standard and its grade."
    if "brand" in t or "make" in t or "manufacturer" in t:
        return "Replace with objective qualification: 'conforming to <IS> and bearing the BIS Standard Mark under a valid licence'."
    return None


OPEN_ENDED = r"\b(as required|as directed|as necessary|as applicable|as per site requirements?|if required|wherever necessary|to the satisfaction of|as decided by)\b"


@rule("SS-AMB-002", "Open-ended discretion", "ambiguity", "minor",
      "Open-ended phrases leave the obligation undefined and are a common source of pre-bid queries.")
def r_open(ctx):
    r = _rule("SS-AMB-002")
    out = []
    for c in ctx.clauses:
        for m in re.finditer(OPEN_ENDED, c.text, re.I):
            out.append(_f(ctx, r, f"Clause {c.key} uses open-ended wording “{m.group(0)}”; the obligation is undefined.", c.key,
                          quote=m.group(0), span=[m.start(), m.end()],
                          suggestion="State the exact condition, frequency or authority (e.g. 'one sample per 20 t lot, at the manufacturer's works, before dispatch')."))
    return out


@rule("SS-MOD-001", "Non-binding modal verb", "drafting", "minor",
      "'should'/'may' create recommendations, not obligations; mandatory requirements must use 'shall'.")
def r_modal(ctx):
    r = _rule("SS-MOD-001")
    out = []
    for q in ctx.reqs:
        c = ctx.clause(q.clause_key)
        if not c or c.section_type not in ("technical", "testing", "certification", "inspection", "acceptance", "packaging", "delivery"):
            continue
        m = re.search(r"\b(should|may)\b", q.text)
        if m and not re.search(r"\bmay be (?:rejected|required)\b", q.text, re.I):
            new = q.text.replace(m.group(0), "shall", 1)
            out.append(_f(ctx, r, f"Clause {c.key}: “{m.group(0)}” makes this requirement non-binding.", c.key,
                          quote=q.text[:160], requirement_ids=[q.id],
                          suggestion=f"Use “shall”: {new[:160]}",
                          fix={"op": "replace", "clause_key": c.key, "find": q.text, "replace": new}))
    return out


# =============================================================================================
# Standards
# =============================================================================================
@rule("SS-STD-001", "Generic standard reference", "standards", "major",
      "References such as 'as per relevant IS codes' do not identify the standard, part, edition or grade.", GFR_144_III)
def r_generic(ctx):
    r = _rule("SS-STD-001")
    out = []
    for c in ctx.clauses:
        for txt, s, e in find_generic_references(c.text):
            dom = (ontology.detect_domains(c.text) or c.domain_hint or ctx.ex.domains or [None])[0]
            ds = ctx.domain_standards.get(dom or "", {})
            test_hint = ""
            if re.search(r"bend", c.text, re.I) and dom == "steel":
                test_hint = " — for bend/re-bend tests cite IS 1599 and the bend requirements of IS 1786:2008"
            sugg = f"Name the exact standard{(' (e.g. ' + ds['resolved'] + ')') if ds.get('resolved') else ''}{test_hint}."
            cited_elsewhere = any(v.get("source") == "cited" for v in ctx.domain_standards.values())
            out.append(_f(ctx, r, f"Clause {c.key} refers to “{txt}” without naming the standard.", c.key, quote=txt, span=[s, e],
                          suggestion=sugg, severity="minor" if cited_elsewhere and not test_hint else "major"))
    return out


@rule("SS-STD-002", "Undated standard reference", "standards", "info",
      "An undated reference means 'latest edition' — which may change between NIT and delivery. Cite the year or add 'with all amendments up to <date>'.")
def r_undated(ctx):
    r = _rule("SS-STD-002")
    out = []
    for res in ctx.resolutions:
        if res["status"] == "undated_current" and res.get("in_force"):
            out.append(_f(ctx, r, f"{res['citation']} in Clause {res['clause_key']} is undated; on {res['as_of']} it resolves to {res['in_force']['is_number']}.",
                          res["clause_key"], quote=res["citation"],
                          suggestion=f"Cite “{res['in_force']['is_number']}” (with all amendments in force on the bid due date).",
                          fix={"op": "replace", "clause_key": res["clause_key"], "find": res["raw"], "replace": res["in_force"]["is_number"]},
                          evidence=[{"type": "standard", "ref": res["in_force"]["is_number"], "detail": res["explanation"], "url": _std_url(res["in_force"]["is_number"])}]))
    return out


@rule("SS-STD-003", "Outdated / withdrawn standard", "standards", "critical",
      "Citing a withdrawn or superseded edition makes the requirement legally and technically unenforceable.", GFR_144_III)
def r_outdated(ctx):
    r = _rule("SS-STD-003")
    out = []
    for res in ctx.resolutions:
        if res["status"] in ("withdrawn", "outdated_edition", "superseded"):
            repl = res.get("replacement") or "the current edition"
            extra = ""
            grade = ctx.ex.grades.get("cement") if "8112" in res["family"] or "12269" in res["family"] else None
            if grade:
                extra = f" ({grade} grade)"
            out.append(_f(ctx, r, f"Clause {res['clause_key']} cites {res['citation']}, which is {res['status'].replace('_', ' ')} as of {res['as_of']}. {res['explanation']}",
                          res["clause_key"], quote=res["raw"],
                          suggestion=f"Replace with {repl}{extra}.",
                          fix={"op": "replace", "clause_key": res["clause_key"], "find": res["raw"], "replace": f"{repl}{extra}"},
                          evidence=[{"type": "temporal", "ref": res["citation"], "detail": res["explanation"], "timeline": res.get("timeline")},
                                    {"type": "standard", "ref": repl, "url": _std_url(repl)}]))
    return out


@rule("SS-STD-004", "Unknown standard designation", "standards", "major",
      "The cited designation is not in the registry; it may be mistyped or not an Indian Standard.")
def r_unknown(ctx):
    r = _rule("SS-STD-004")
    return [_f(ctx, r, f"{res['citation']} (Clause {res['clause_key']}) could not be verified in the standards registry.", res["clause_key"],
               quote=res["raw"], suggestion="Verify the number/part/year on standards.bis.gov.in.", confidence=0.7)
            for res in ctx.resolutions if res["status"] == "unknown" and res.get("body") == "BIS"]


@rule("SS-STD-005", "Amendments not acknowledged", "standards", "info",
      "Published amendments change clause requirements; the tender should state which amendments apply.")
def r_amend(ctx):
    r = _rule("SS-STD-005")
    out = []
    txt = ctx.full_text().lower()
    if re.search(r"amendments?|amended up to|latest amendment", txt):
        return out
    seen = set()
    for res in ctx.resolutions:
        n = len(res.get("amendments_in_force") or [])
        if n and res["status"] in ("current", "undated_current") and res["family"] not in seen:
            seen.add(res["family"])
            nums = ", ".join(f"Amd {a['number']}" for a in res["amendments_in_force"])
            out.append(_f(ctx, r, f"{res['in_force']['is_number']} has {n} amendment(s) in force ({nums}) that the tender does not mention.",
                          res["clause_key"], quote=res["raw"],
                          suggestion=f"Write “{res['in_force']['is_number']} including all amendments in force on the last date of bid submission”.",
                          evidence=[{"type": "amendment", "ref": f"{res['in_force']['is_number']} {a['title'] or 'Amd ' + str(a['number'])}",
                                     "detail": a.get("summary"), "date": a.get("published_at")} for a in res["amendments_in_force"]]))
    return out


@rule("SS-STD-007", "Amendment coming into force during tender", "standards", "major",
      "An amendment to a cited standard becomes effective after publication — bids and inspection may be judged against different text.")
def r_amend_pending(ctx):
    r = _rule("SS-STD-007")
    out, seen = [], set()
    for res in ctx.resolutions:
        for a in res.get("amendments_pending") or []:
            k = (res["family"], a["number"])
            if k in seen:
                continue
            seen.add(k)
            title = a.get("title") or f"Amendment {a['number']}"
            out.append(_f(ctx, r, f"{title}{'' if res['family'] in title else ' to ' + res['family']} takes effect on {a.get('effective_from')} — after the tender date {res['as_of']}.",
                          res["clause_key"], quote=res["raw"],
                          suggestion="State which version governs supplies (e.g. 'including amendments in force on the date of delivery') and brief bidders.",
                          evidence=[{"type": "amendment", "ref": a.get("title"), "detail": a.get("summary"), "date": a.get("effective_from")}]))
    return out


@rule("SS-STD-008", "Standard revision takes effect during contract", "standards", "major",
      "The edition in force today is replaced before delivery completes.")
def r_revision_pending(ctx):
    from datetime import date as _date, timedelta
    r = _rule("SS-STD-008")
    out, seen = [], set()
    horizon = ctx.as_of + timedelta(days=int((ctx.delivery_days() or 90) + 365))
    for res in ctx.resolutions:
        inf = res.get("in_force") or {}
        to = inf.get("effective_to")
        if to and inf.get("is_number") not in seen and ctx.as_of < _date.fromisoformat(to) <= horizon:
            seen.add(inf.get("is_number"))
            succ = next((t for t in res.get("timeline", []) if t.get("from") and t["from"] > to[:10]), None) or {}
            out.append(_f(ctx, r, f"{inf['is_number']} ceases on {to}; {succ.get('is_number') or 'a new edition'} takes over during the contract period.",
                          res["clause_key"], quote=res.get("raw"),
                          suggestion="Decide and state which edition applies to supplies after the changeover (issue a corrigendum if needed)."))
    return out


@rule("SS-STD-006", "Missing normative / test reference", "completeness", "major",
      "The governing standard normatively depends on test-method or safety standards the tender never mentions.")
def r_missing_dep(ctx):
    r = _rule("SS-STD-006")
    out = []
    for g in ctx.missing_dependencies:
        out.append(_f(ctx, r, g["description"], g.get("clause_key"), severity="major" if g["relationship_type"] in ("test_method", "safety_requirement") else "minor",
                      suggestion=g["suggestion"],
                      evidence=[{"type": "graph_edge", "ref": f"{g['affected_standard']} → {g['mandated_standard']}",
                                 "detail": f"{g['relationship_type'].replace('_', ' ')} ({g.get('graph_clause') or 'normative reference'})"}]))
    return out


# =============================================================================================
# Units & tolerances
# =============================================================================================
@rule("SS-UNIT-001", "Value without unit", "measurability", "major", "A number without a unit cannot be evaluated.")
def r_nounit(ctx):
    r = _rule("SS-UNIT-001")
    out = []
    for q in ctx.reqs:
        if "no_unit" in q.flags:
            canon = ontology.param_unit(q.parameter).replace("**2", "²")
            val = q.matched_text or ""
            num = re.search(r"\d+(?:\.\d+)?", val)
            fix = None
            if num:
                fix = {"op": "replace", "clause_key": q.clause_key, "find": q.text, "replace": q.text.replace(num.group(0), f"{num.group(0)} {canon}", 1)}
            out.append(_f(ctx, r, f"Clause {q.clause_key}: {q.parameter_label} is specified as {val.strip()} with no unit.", q.clause_key,
                          quote=q.text, requirement_ids=[q.id], suggestion=f"State the unit explicitly (expected: {canon}).", fix=fix))
    return out


@rule("SS-UNIT-002", "Non-SI unit", "measurability", "minor", "Use SI units as in the Indian Standards (e.g. MPa / N/mm² instead of kg/cm²).")
def r_nonsi(ctx):
    r = _rule("SS-UNIT-002")
    return [_f(ctx, r, f"Clause {q.clause_key} uses non-SI unit '{q.unit_raw}'.", q.clause_key, quote=q.text, requirement_ids=[q.id],
               suggestion=f"Convert to {q.norm.get('unit')} (normalised value used by SpecSure: {q.norm.get('min') or q.norm.get('max')}).")
            for q in ctx.reqs if "non_si_unit" in q.flags]


@rule("SS-UNIT-003", "Inconsistent units", "measurability", "minor", "The same parameter is expressed in different units in different clauses.")
def r_unit_mix(ctx):
    r = _rule("SS-UNIT-003")
    by: Dict[str, List[Requirement]] = {}
    for q in ctx.reqs:
        if q.kind == "parameter" and q.unit_raw:
            by.setdefault(f"{q.domain}.{q.parameter}", []).append(q)
    out = []
    for k, qs in by.items():
        units = {q.unit_raw.lower().replace(" ", "") for q in qs}
        if len(units) > 1:
            out.append(_f(ctx, r, f"{qs[0].parameter_label} is written in {', '.join(sorted(units))} across clauses {', '.join(sorted({q.clause_key for q in qs}))}.",
                          qs[0].clause_key, requirement_ids=[q.id for q in qs], suggestion="Use one unit consistently."))
    return out


@rule("SS-TOL-001", "Missing tolerance", "measurability", "minor", "Dimensional values need a tolerance (or a reference to the standard's tolerance table).")
def r_tol(ctx):
    r = _rule("SS-TOL-001")
    out = []
    for q in ctx.reqs:
        if "no_tolerance" in q.flags:
            ds = ctx.domain_standards.get(q.domain or "", {})
            std = ds.get("resolved")
            out.append(_f(ctx, r, f"Clause {q.clause_key}: {q.parameter_label} has no tolerance.", q.clause_key, quote=q.text, requirement_ids=[q.id],
                          suggestion=f"Add '… with tolerances on nominal size and mass per metre as per {std}'." if std else "Specify ± tolerance."))
    return out


# =============================================================================================
# Testing, inspection, acceptance
# =============================================================================================
@rule("SS-TEST-001", "Parameter without test method", "testing", "major",
      "Every acceptance parameter needs a test method; otherwise bidders and inspectors may test differently.")
def r_test_method(ctx):
    r = _rule("SS-TEST-001")
    cited = {ref["family"] for ref in ctx.ex.citations}
    cited_base = {re.sub(r"\s*\(.*\)$", "", f) for f in cited}
    by_test: Dict[str, List[Requirement]] = {}
    for q in ctx.reqs:
        if q.kind != "parameter":
            continue
        t = ontology.param_test(q.parameter)
        if not t:
            continue
        fam = t["standard"]
        if fam in cited or re.sub(r"\s*\(.*\)$", "", fam) in cited_base:
            continue
        by_test.setdefault(fam, []).append(q)
    out = []
    for fam, qs in by_test.items():
        t = ontology.param_test(qs[0].parameter)
        labels = ", ".join(sorted({q.parameter_label for q in qs}))
        keys = sorted({q.clause_key for q in qs})
        last = keys[-1]
        out.append(_f(ctx, r, f"No test method is specified for {labels} (Clauses {', '.join(keys)}).", keys[0], requirement_ids=[q.id for q in qs],
                      suggestion=f"Add: '{labels} shall be determined as per {fam} ({t['name']}) in a NABL-accredited laboratory.'",
                      fix={"op": "append", "clause_key": last, "text": f"{labels} shall be determined as per {fam} in a NABL-accredited laboratory."},
                      evidence=[{"type": "ontology", "ref": fam, "detail": f"{t['name']} — {t['discipline']} lab, ~{t['days']} day(s)"}]))
    return out


@rule("SS-TEST-002", "No accredited laboratory", "testing", "minor", "Test reports should come from NABL-accredited (ISO/IEC 17025) laboratories.")
def r_nabl(ctx):
    r = _rule("SS-TEST-002")
    txt = ctx.full_text()
    if re.search(r"\bNABL\b|17025|accredited", txt, re.I):
        return []
    test_reqs = [q for q in ctx.reqs if q.kind == "testing"]
    if not test_reqs:
        return []
    q = test_reqs[0]
    return [_f(ctx, r, "Testing is required but the tender does not specify who may test (manufacturer / NABL laboratory / third party).", q.clause_key,
               quote=q.text, suggestion="Add: 'Test reports shall be from a NABL-accredited laboratory (ISO/IEC 17025) with the test in its scope of accreditation.'",
               fix={"op": "append", "clause_key": q.clause_key, "text": "Test reports shall be issued by a NABL-accredited laboratory having the test in its scope of accreditation."})]


@rule("SS-ACC-001", "No acceptance / sampling criteria", "completeness", "major",
      "Without a sampling plan and lot acceptance/rejection criteria, conformity cannot be decided objectively.")
def r_acceptance(ctx):
    r = _rule("SS-ACC-001")
    if any(q.kind == "acceptance" for q in ctx.reqs) or re.search(r"sampling|lot (?:shall be )?(?:accepted|rejected)|AQL|rejection", ctx.full_text(), re.I):
        return []
    key = next((c.key for c in ctx.clauses if c.section_type in ("testing", "inspection")), ctx.clauses[-1].key if ctx.clauses else None)
    return [_f(ctx, r, "The tender has no sampling plan or lot acceptance / rejection criteria.", key,
               suggestion="Add an acceptance clause: sampling as per the relevant IS (or IS 2500 (Part 1)), re-test rules, and rejection of non-conforming lots.",
               fix={"op": "add_clause", "after_key": key, "text": "Acceptance: Sampling and criteria for conformity shall be as per the relevant Indian Standard (or IS 2500 (Part 1) where not specified). A lot failing any requirement on re-test shall be rejected and replaced at the supplier's cost."})]


@rule("SS-INS-001", "Discretionary / missing inspection", "completeness", "minor", "Inspection stage, authority and cost must be defined.")
def r_inspection(ctx):
    r = _rule("SS-INS-001")
    ins = [q for q in ctx.reqs if q.kind == "inspection"]
    if not ins:
        return [_f(ctx, r, "No inspection clause found.", None, suggestion="Define pre-dispatch / on-site inspection, inspecting authority and cost bearer.")]
    out = []
    for q in ins:
        if q.modality in ("may",) or re.search(OPEN_ENDED, q.text, re.I):
            out.append(_f(ctx, r, f"Clause {q.clause_key}: inspection is discretionary (“{q.modality}”) and its stage is undefined.", q.clause_key, quote=q.text,
                          suggestion="State: stage (pre-dispatch / receipt), authority, sampling rate and who bears testing cost."))
    return out


# =============================================================================================
# Certification / QCO
# =============================================================================================
@rule("SS-CERT-001", "Mandatory certification not required", "certification", "critical",
      "Products under a Quality Control Order / CRS can only be sold with a valid BIS licence / registration; the tender must require it.")
def r_cert_missing(ctx):
    r = _rule("SS-CERT-001")
    out = []
    for dom, ds in ctx.domain_standards.items():
        regs = ds.get("regulations_in_force") or []
        mand = [g for g in regs if (g.get("is_mandatory") or "yes") == "yes"]
        if not mand:
            continue
        dom_clauses = [c for c in ctx.clauses if dom in (ontology.detect_domains(c.heading + " " + c.text) or c.domain_hint or [])]
        dom_text = " ".join(c.text for c in dom_clauses)
        if re.search(r"\bISI\b|BIS (?:standard )?mark|BIS licen[cs]e|CM/L|standard mark|registration (?:no|number)|\bCRS\b|R-\d{8}", dom_text, re.I):
            continue
        key = ds.get("clause_key") or (dom_clauses[0].key if dom_clauses else None)
        g = mand[0]
        mark = "BIS registration (CRS) with R-number" if g.get("regulation_type") == "CRS" else "BIS Standard Mark (ISI) under a valid licence (CM/L)"
        out.append(_f(ctx, r, f"{dom.title()} ({ds.get('resolved')}) is covered by “{g['title']}”, but the tender does not require {mark}.", key,
                      suggestion=f"Add: 'The material shall bear the {mark} as per {ds.get('resolved')}; licence details shall be furnished with the bid and verified on the BIS portal.'",
                      fix={"op": "append", "clause_key": key, "text": f"The material shall bear the {mark} as per {ds.get('resolved')}; the licence number shall be furnished with the bid."},
                      evidence=[{"type": "regulation", "ref": g["title"], "detail": f"{g.get('scheme')} — verification: {g.get('verification_state')}",
                                 "url": g.get("source_url"), "date": g.get("effective_from")}]))
    return out


@rule("SS-CERT-002", "QCO coming into force", "certification", "major", "A regulation takes effect before delivery completes; bids must plan for it.")
def r_cert_upcoming(ctx):
    r = _rule("SS-CERT-002")
    out = []
    for dom, ds in ctx.domain_standards.items():
        for g in ds.get("regulations_upcoming") or []:
            out.append(_f(ctx, r, f"“{g['title']}” comes into force on {g['effective_from']} — within the contract period for {dom}.", ds.get("clause_key"),
                          suggestion="State explicitly that supplies after the enforcement date must carry the mandated certification.",
                          evidence=[{"type": "regulation", "ref": g["title"], "date": g["effective_from"], "url": g.get("source_url")}]))
    return out


# =============================================================================================
# Contradictions (formal)
# =============================================================================================
@rule("SS-CON-001", "Contradictory requirements (formally proven)", "contradiction", "critical",
      "An SMT solver proved that no product can satisfy these clauses together (minimal unsatisfiable subset).")
def r_contra(ctx):
    r = _rule("SS-CON-001")
    out = []
    if not ctx.verification:
        return out
    for cf in ctx.verification.conflicts:
        keys = sorted({a.clause_key for a in cf.atoms if a.clause_key})
        out.append(_f(ctx, r, cf.explanation, keys[0] if keys else None, source="solver", confidence=1.0,
                      requirement_ids=[a.label for a in cf.atoms if a.kind == "requirement"],
                      quote=" ⟂ ".join(a.text[:90] for a in cf.atoms if a.kind == "requirement"),
                      suggestion="Reconcile the clauses (keep the value required by the governing standard) and issue a corrigendum.",
                      evidence=[{"type": "solver", "ref": ctx.verification.engine, "detail": cf.witness or "UNSAT core", "clauses": keys,
                                 "core": [a.to_dict() for a in cf.atoms]}]))
    return out


@rule("SS-CON-002", "Requirement contradicts cited standard", "contradiction", "critical",
      "The tender requires conformity to a standard AND a value that the same standard forbids.")
def r_contra_std(ctx):
    r = _rule("SS-CON-002")
    out = []
    if not ctx.verification:
        return out
    for cf in ctx.verification.standard_conflicts:
        req = next((a for a in cf.atoms if a.kind == "requirement"), None)
        std = next((a for a in cf.atoms if a.kind == "standard"), None)
        if not req or not std:
            continue
        out.append(_f(ctx, r, f"Clause {req.clause_key} ({req.description}) is incompatible with {std.description}.", req.clause_key, source="solver",
                      confidence=0.97, requirement_ids=[req.label], quote=req.text,
                      suggestion="Align the clause with the cited standard or justify the deviation explicitly.",
                      evidence=[{"type": "solver", "ref": ctx.verification.engine, "detail": cf.witness}, {"type": "standard_parameter", "ref": std.label.replace('STD:', '')}]))
    return out


@rule("SS-CON-003", "Requirement weaker than cited standard", "contradiction", "major",
      "The clause permits values the cited standard/grade does not allow — which one governs is ambiguous.")
def r_weaker(ctx):
    r = _rule("SS-CON-003")
    out = []
    for q in ctx.reqs:
        if q.kind != "parameter" or q.op == "enum":
            continue
        ds = ctx.domain_standards.get(q.domain or "", {})
        sp = ontology.standards_parameters().get(ds.get("family") or "")
        if not sp:
            continue
        grade = ds.get("grade") if ds.get("grade") in sp["grades"] else sp.get("default_grade")
        b = sp["grades"].get(grade, {}).get(q.parameter)
        if not b:
            continue
        lo, hi = q.norm.get("min"), q.norm.get("max")
        msg = None
        new = None
        if lo is not None and b.get("min") is not None and lo < b["min"] - 1e-9 and hi is None:
            msg = f"Clause {q.clause_key} accepts {q.parameter_label} ≥ {lo:g} but {ds['family']} {grade} requires ≥ {b['min']:g}."
            new = b["min"]
        if hi is not None and b.get("max") is not None and hi > b["max"] + 1e-9 and lo is None:
            msg = f"Clause {q.clause_key} accepts {q.parameter_label} ≤ {hi:g} but {ds['family']} {grade} requires ≤ {b['max']:g}."
            new = b["max"]
        if msg:
            fix = None
            if q.matched_text:
                num = re.search(r"\d+(?:\.\d+)?", q.matched_text)
                if num:
                    new_txt = q.text.replace(q.matched_text, q.matched_text.replace(num.group(0), f"{new:g}", 1), 1)
                    fix = {"op": "replace", "clause_key": q.clause_key, "find": q.text, "replace": new_txt}
            out.append(_f(ctx, r, msg, q.clause_key, quote=q.text, requirement_ids=[q.id], fix=fix,
                          suggestion=f"Use the standard's limit ({new:g}) or delete the clause and rely on the standard.",
                          evidence=[{"type": "standard_parameter", "ref": f"{ds['family']} {grade}", "detail": f"{q.parameter_label}: {b}"}]))
    return out


@rule("SS-CON-004", "Inconsistent tender dates", "contradiction", "major", "Key dates are out of sequence.")
def r_dates(ctx):
    r = _rule("SS-CON-004")
    d = ctx.ex.dates
    out = []

    def key_for(role):
        q = next((q for q in ctx.reqs if f"date:{role}" in q.tags), None)
        return q.clause_key if q else None
    if d.get("prebid") and d.get("bid_due") and d["prebid"] >= d["bid_due"]:
        out.append(_f(ctx, r, f"Pre-bid meeting ({d['prebid']}) is on/after the last date of bid submission ({d['bid_due']}) — bidders cannot use the clarifications.",
                      key_for("prebid"), suggestion="Hold the pre-bid meeting well before the bid due date (GFR 2017 Rule 173(x)) or extend the due date.",
                      basis="GFR 2017 Rule 173(x): pre-bid conference to clarify specifications before bid submission."))
    if d.get("publication") and d.get("bid_due") and d["bid_due"] <= d["publication"]:
        out.append(_f(ctx, r, "Bid due date is not after publication date.", key_for("bid_due"), suggestion="Correct the schedule."))
    if d.get("publication") and d.get("bid_due"):
        from datetime import date as _d
        days = (_d.fromisoformat(d["bid_due"]) - _d.fromisoformat(d["publication"])).days
        if 0 < days < 21:
            out.append(_f(ctx, r, f"Only {days} days between publication and bid due date.", key_for("bid_due"), severity="minor",
                          suggestion="Allow adequate time for bid preparation (commonly ≥ 21 days for open tenders; check applicable manual)."))
    return out


@rule("SS-CON-005", "Delivery period shorter than mandatory testing", "contradiction", "critical",
      "The tender demands a test before dispatch that takes longer than the whole delivery period.")
def r_delivery_test(ctx):
    r = _rule("SS-CON-005")
    days = ctx.delivery_days()
    if days is None:
        return []
    out = []
    for q in ctx.reqs:
        if q.kind not in ("testing",) or not re.search(r"prior to dispatch|before dispatch|pre-dispatch|before supply|with (?:each|the) consignment", q.text, re.I):
            continue
        params = ontology.find_parameters(q.text, ontology.detect_domains(q.text) or ctx.ex.domains)
        for pid, _, _ in params:
            t = ontology.param_test(pid)
            if t and t["days"] > days:
                dq = next((x for x in ctx.reqs if x.parameter == "delivery_period"), None)
                out.append(_f(ctx, r, f"Clause {q.clause_key} requires {ontology.param_label(pid)} testing before dispatch (~{t['days']} days incl. curing, {t['standard']}), "
                                      f"but Clause {dq.clause_key if dq else '?'} allows only {days:g} days for complete delivery.",
                              q.clause_key, quote=q.text, requirement_ids=[q.id] + ([dq.id] if dq else []),
                              suggestion=f"Either extend delivery to ≥ {t['days'] + 5} days, or accept the manufacturer's certificate for the lot and verify {ontology.param_label(pid).lower()} on retained samples after delivery.",
                              evidence=[{"type": "test_duration", "ref": t["standard"], "detail": f"{t['name']}: ~{t['days']} days"}]))
                break
    return out


# =============================================================================================
# Restriction / competition
# =============================================================================================
@rule("SS-RES-001", "Brand name specified", "restriction", "critical",
      "Naming brands restricts competition; if unavoidable it must be followed by 'or equivalent' with objective criteria.", GFR_144)
def r_brand(ctx):
    r = _rule("SS-RES-001")
    out = []
    lex = ontology.brand_lexicon()
    for c in ctx.clauses:
        found = []
        for cat, names in lex.items():
            for n in names:
                m = re.search(r"(?<![A-Za-z])" + re.escape(n) + r"(?![A-Za-z])", c.text)
                if m:
                    found.append((n, m.start(), m.end()))
        if not found:
            continue
        has_equiv = bool(re.search(r"or (?:substantially )?equivalent|or equal", c.text, re.I))
        exclusive = bool(re.search(r"\bonly\b|\bexclusively\b", c.text, re.I))
        names = ", ".join(sorted({f[0] for f in found}))
        dom = (ontology.detect_domains(c.text) or c.domain_hint or ctx.ex.domains or [""])[0]
        std = ctx.domain_standards.get(dom, {}).get("resolved") or "the relevant Indian Standard"
        new_text = f"{c.heading}: Material of any make conforming to {std} and bearing the BIS Standard Mark under a valid licence shall be acceptable."
        out.append(_f(ctx, r, f"Clause {c.key} names brand(s) {names}{' exclusively' if exclusive else ''}{'' if has_equiv else ' without “or equivalent”'}.",
                      c.key, severity="critical" if (exclusive or not has_equiv) else "major", quote=c.text[:200],
                      span=[found[0][1], found[-1][2]],
                      suggestion=f"Replace with objective, brand-neutral criteria: “{new_text}”",
                      fix={"op": "replace_clause", "clause_key": c.key, "text": new_text.split(": ", 1)[1]},
                      evidence=[{"type": "policy", "ref": "GFR 2017 Rule 144(i)(b)", "detail": "Specifications should not indicate a particular trademark, trade name or brand."}]))
    return out


@rule("SS-RES-002", "Proprietary / single-source wording", "restriction", "major", "Model numbers, 'approved makes' or OEM-only clauses narrow competition.", GFR_144)
def r_proprietary(ctx):
    r = _rule("SS-RES-002")
    out = []
    pats = ontology.load_json("brand_lexicon.json")["proprietary_patterns"]
    for c in ctx.clauses:
        for p in pats:
            m = re.search(p, c.text, 0 if ("OEM" in p or "odel" in p) else re.I)
            if m and not re.search(r"\bmake\s*:\s*(?:any|reputed)", m.group(0), re.I):
                out.append(_f(ctx, r, f"Clause {c.key} contains proprietary wording “{m.group(0)}”.", c.key, quote=m.group(0), span=[m.start(), m.end()],
                              suggestion="Describe the functional requirement instead of a make/model."))
                break
    return out


@rule("SS-RES-003", "Restrictive parameter (market evidence)", "restriction", "major",
      "A single clause, stricter than the cited standard, eliminates most manufacturers who could otherwise comply.", GFR_144)
def r_restrictive(ctx):
    r = _rule("SS-RES-003")
    out = []
    for m in ctx.market:
        for imp in m["clause_impacts"]:
            if imp["verdict"] not in ("restrictive", "tighter_than_standard"):
                continue
            q = next((x for x in ctx.reqs if x.id == imp["label"]), None)
            sev = "critical" if imp["verdict"] == "restrictive" and not m["competition_ok"] else ("major" if imp["verdict"] == "restrictive" else "minor")
            sb = imp["standard_bounds"]
            fix = None
            if q and q.matched_text:
                std_val = sb[1] if imp["tender_bounds"][1] is not None else sb[0]
                num = re.search(r"\d+(?:\.\d+)?", q.matched_text)
                if num and std_val is not None:
                    fix = {"op": "replace", "clause_key": q.clause_key, "find": q.text,
                           "replace": q.text.replace(q.matched_text, q.matched_text.replace(num.group(0), f"{std_val:g}", 1), 1)}
            out.append(_f(ctx, r, f"Clause {imp['clause_key']} ({imp['description'][:70]}) is stricter than {m['standard']} and excludes "
                                  f"{imp['manufacturers_excluded_by_this_clause']} of {imp['manufacturers_if_removed']} otherwise-eligible manufacturers "
                                  f"(eligible after all clauses: {m['eligible_manufacturers']}).",
                          imp["clause_key"], severity=sev, source="market", confidence=0.8, requirement_ids=[imp["label"]], quote=q.text if q else None,
                          suggestion=(f"Relax to the standard limit {sb} → {imp['manufacturers_if_relaxed_to_standard']} manufacturers eligible, "
                                      "or record a technical justification for the tighter limit."),
                          fix=fix,
                          evidence=[{"type": "market", "ref": "product-space analysis", "detail": m["catalogue_note"],
                                     "excluded": imp["excluded_manufacturers"], "funnel": m["funnel"]}]))
    return out


@rule("SS-RES-004", "Insufficient competition", "restriction", "critical", "Fewer than three manufacturers can meet the combined specification.", GFR_144)
def r_competition(ctx):
    r = _rule("SS-RES-004")
    out = []
    for m in ctx.market:
        if not m["competition_ok"]:
            top = next((i for i in m["clause_impacts"] if i["manufacturers_excluded_by_this_clause"] > 0), None)
            out.append(_f(ctx, r, f"Only {m['eligible_manufacturers']} manufacturer(s) of {m['legal_manufacturers']} licensed ones can meet the {m['domain']} specification"
                                  + (f"; the most restrictive clause is {top['clause_key']}." if top else "."),
                          top["clause_key"] if top else None, source="market", confidence=0.8,
                          suggestion="Review restrictive clauses (see funnel) before publication; single-source outcomes need recorded justification.",
                          evidence=[{"type": "market", "ref": "funnel", "funnel": m["funnel"]}]))
    return out


@rule("SS-RES-005", "Restrictive eligibility wording", "restriction", "major",
      "Eligibility tied to a specific past buyer, OEM-only supply or disproportionate thresholds narrows competition.", GFR_144)
def r_eligibility(ctx):
    r = _rule("SS-RES-005")
    pats = [r"(?:supplied|executed)\s+(?:to|for)\s+(?:this|the same)\s+(?:department|organisation|office)",
            r"\bonly\s+(?:original\s+equipment\s+manufacturers?|OEMs?)\b", r"\bauthori[sz]ed\s+dealers?\s+of\s+[A-Z]",
            r"\bmust\s+have\s+(?:a\s+)?(?:factory|plant|office)\s+(?:in|at)\s+[A-Z][a-z]+"]
    out = []
    for c in ctx.clauses:
        for p_ in pats:
            m = re.search(p_, c.text, re.I)
            if m:
                out.append(_f(ctx, r, f"Clause {c.key} restricts eligibility: “{m.group(0)}”.", c.key, quote=m.group(0),
                              suggestion="Use objective capability criteria (similar-work value/quantity, licences, test facilities) applicable to any supplier."))
                break
    return out


@rule("SS-CERT-003", "Certification scheme mismatch", "certification", "major",
      "The tender asks for a different conformity scheme than the one the regulation mandates (ISI licence vs CRS registration).")
def r_scheme(ctx):
    r = _rule("SS-CERT-003")
    out = []
    for dom, ds in ctx.domain_standards.items():
        regs = ds.get("regulations_in_force") or []
        if not regs:
            continue
        dom_text = " ".join(c.text for c in ctx.clauses if dom in (ontology.detect_domains(c.heading + " " + c.text) or c.domain_hint or []))
        asks_isi = bool(re.search(r"\bISI\b|CM/L|standard mark", dom_text, re.I))
        asks_crs = bool(re.search(r"\bCRS\b|compulsory registration|R-number|registration number", dom_text, re.I))
        crs = any(g.get("regulation_type") == "CRS" for g in regs)
        if crs and asks_isi and not asks_crs:
            out.append(_f(ctx, r, f"{dom.title()} falls under the Compulsory Registration Scheme, but the tender asks for an ISI licence.", ds.get("clause_key"),
                          suggestion="Ask for BIS CRS registration (R-number) for the model offered."))
        if not crs and asks_crs and not asks_isi:
            out.append(_f(ctx, r, f"{dom.title()} is under a Scheme-I (ISI) order, but the tender asks for CRS registration.", ds.get("clause_key"),
                          suggestion="Ask for a valid BIS licence (CM/L) under Scheme-I."))
    return out


@rule("SS-CERT-004", "Foreign standard accepted for QCO product", "certification", "critical",
      "Where a Quality Control Order mandates an Indian Standard, conformity to BS/EN/ASTM alone does not make the product legally saleable.")
def r_foreign(ctx):
    r = _rule("SS-CERT-004")
    out = []
    for res in ctx.resolutions:
        if res.get("status") != "foreign":
            continue
        c = ctx.clause(res["clause_key"])
        doms = ontology.detect_domains((c.heading + " " + c.text) if c else "") or (c.domain_hint if c else []) or ctx.ex.domains
        for d in doms:
            ds = ctx.domain_standards.get(d, {})
            if any((g.get("is_mandatory") or "yes") == "yes" for g in ds.get("regulations_in_force", [])):
                out.append(_f(ctx, r, f"Clause {res['clause_key']} accepts {res['citation']}, but {d} products are under a mandatory order requiring {ds.get('resolved')}.",
                              res["clause_key"], quote=res.get("raw"),
                              suggestion=f"Accept only material certified to {ds.get('resolved')} (foreign standards may be referenced for information only)."))
                break
    return out


@rule("SS-UNIT-004", "Physically impossible value", "measurability", "critical",
      "A value outside its physical range (e.g. > 100 %, pH > 14, negative strength) cannot be met by any product.")
def r_impossible(ctx):
    r = _rule("SS-UNIT-004")
    out = []
    for q in ctx.reqs:
        if q.kind != "parameter":
            continue
        u = q.norm.get("unit")
        vals = [v for v in (q.norm.get("min"), q.norm.get("max")) if v is not None]
        bad = any(v < 0 for v in vals) or (u == "percent" and any(v > 100 for v in vals)) or (q.parameter == "ph" and any(v > 14 for v in vals)) \
            or (q.parameter == "ip_rating" and any(v > 69 for v in vals)) or (q.parameter == "power_factor" and any(v > 1 for v in vals))
        if bad:
            out.append(_f(ctx, r, f"Clause {q.clause_key}: {q.parameter_label} value {vals} is outside the physically possible range.", q.clause_key,
                          quote=q.text, requirement_ids=[q.id], suggestion="Correct the value / unit (likely a typo)."))
    return out


# =============================================================================================
# Structure & completeness
# =============================================================================================
@rule("SS-DUP-001", "Duplicate clause", "drafting", "minor", "Near-identical clauses drift apart in corrigenda and create contradictions.")
def r_dup(ctx):
    r = _rule("SS-DUP-001")
    try:
        from rapidfuzz import fuzz
        sim = lambda a, b: fuzz.token_set_ratio(a, b)
    except Exception:
        import difflib
        sim = lambda a, b: 100 * difflib.SequenceMatcher(None, a, b).ratio()
    out = []
    cl = [c for c in ctx.clauses if len(c.text) > 30]
    doms = {c.key: set(ontology.detect_domains(c.heading + " " + c.text) or c.domain_hint or []) for c in cl}
    for i, a in enumerate(cl):
        for b in cl[i + 1:]:
            if doms[a.key] and doms[b.key] and not (doms[a.key] & doms[b.key]):
                continue   # same boilerplate for different products (multi-item tender) is not a duplicate
            s = sim(_replace_nums(a.text.lower()), _replace_nums(b.text.lower()))
            if s >= 92:
                out.append(_f(ctx, r, f"Clause {b.key} duplicates Clause {a.key} ({s:.0f}% similar).", b.key, quote=b.text[:160],
                              suggestion=f"Delete Clause {b.key} or merge it into Clause {a.key}.",
                              fix={"op": "delete_clause", "clause_key": b.key}))
    return out


def _replace_nums(s: str) -> str:
    from app.engine.extractor import _replace_number_words
    return _replace_number_words(s)


ESSENTIAL = {
    "steel": ["yield_strength", "tensile_strength", "elongation", "total_elongation_max_force", "carbon", "sulphur", "phosphorus"],
    "cement": ["compressive_strength_28d", "initial_setting_time", "final_setting_time", "fineness", "soundness_le_chatelier"],
    "cables": ["voltage_grade", "conductor_resistance", "insulation_thickness"],
    "water": ["ph", "tds"],
}


@rule("SS-CMP-001", "Essential parameter not addressed", "completeness", "info",
      "An essential parameter of the product standard is neither specified nor covered by an explicit 'conforming to <IS>' clause.")
def r_essential(ctx):
    r = _rule("SS-CMP-001")
    out = []
    for dom, params in ESSENTIAL.items():
        ds = ctx.domain_standards.get(dom)
        if not ds:
            continue
        present = {q.parameter for q in ctx.reqs if q.domain == dom}
        missing = [p for p in params if p not in present]
        if not missing:
            continue
        covered = ds.get("status") in ("current", "undated_current")
        out.append(_f(ctx, r, f"{dom.title()}: {', '.join(ontology.param_label(p) for p in missing)} not stated explicitly"
                              + (f" (covered only implicitly via {ds.get('resolved')})." if covered else " and the governing standard citation is not valid."),
                      ds.get("clause_key"), severity="info" if covered else "major",
                      suggestion=f"Either list them with limits or state 'all requirements of {ds.get('resolved')} ({ds.get('grade') or 'grade'}) shall apply'."))
    return out


@rule("SS-DATE-001", "Relative period without anchor", "drafting", "minor", "'within N days' must say from which event.")
def r_anchor(ctx):
    r = _rule("SS-DATE-001")
    return [_f(ctx, r, f"Clause {q.clause_key}: period without a start event.", q.clause_key, quote=q.text, requirement_ids=[q.id],
               suggestion="Add the anchor event, e.g. 'from the date of issue of Purchase Order'.")
            for q in ctx.reqs if "relative_date_without_anchor" in q.flags]


@rule("SS-SEC-001", "Embedded instruction / prompt-injection text", "security", "major",
      "Documents containing instructions aimed at AI systems are quarantined from LLM prompts.")
def r_injection(ctx):
    from app.engine.guardrails import scan_injection
    r = _rule("SS-SEC-001")
    out = []
    for c in ctx.clauses:
        for hit in scan_injection(c.text):
            out.append(_f(ctx, r, f"Clause {c.key} contains text that looks like an instruction to an AI system: “{hit['match'][:80]}”.", c.key,
                          quote=hit["match"], suggestion="Treat as suspicious; this text is excluded from any LLM prompt and should be reviewed."))
    return out


# =============================================================================================
def run_all(ctx: CompileContext) -> List[Finding]:
    findings: List[Finding] = []
    for r in RULES:
        try:
            findings.extend(r.fn(ctx))
        except Exception as e:  # a buggy rule must never break compilation
            findings.append(Finding(rule_id=r.id, rule_name=r.name, category="internal", severity="info",
                                    message=f"Rule {r.id} failed: {e}", source="internal"))
    uniq: Dict[str, Finding] = {}
    for f in findings:
        f.finalize()
        uniq.setdefault(f.fingerprint, f)
    return sorted(uniq.values(), key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), _clause_sort(f.clause_key)))


def _clause_sort(k: Optional[str]):
    if not k:
        return (999,)
    parts = re.findall(r"\d+", k)
    return tuple(int(p) for p in parts) or (998,)


def rules_catalog() -> List[dict]:
    return [{"id": r.id, "name": r.name, "category": r.category, "default_severity": r.severity,
             "description": r.description, "basis": r.basis} for r in RULES]
