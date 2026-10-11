"""
Market Feasibility & Specification-Restriction analysis ("product-space model counting").

Question answered: *how many real products / manufacturers could legally bid against this
specification, and which exact clause shrinks that set?*  GFR 2017 Rule 144(i) asks for
specifications that are "objective, functional, generic and measurable" and that do not favour a
brand; this module turns that principle into evidence:

  funnel        products remaining after each clause is applied, in document order
  leave-one-out how many extra manufacturers become eligible if ONE clause is relaxed to the
                level of the cited Indian Standard (or removed)
  verdict       'restrictive' when a single clause stricter than the standard eliminates most of
                the otherwise-eligible manufacturers or leaves < 3 competing manufacturers.

The catalogue is pluggable (GeM catalogue / BIS licence data in production; a synthetic, clearly
labelled catalogue in this demo). The output is decision support for a human reviewer, never an
automatic verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.engine import ontology
from app.engine.extractor import Requirement

MIN_COMPETITION = 3


def catalog() -> List[dict]:
    try:
        return ontology.load_json("market_catalog.json")["products"]
    except FileNotFoundError:
        return []


@dataclass
class Gate:
    label: str
    clause_key: Optional[str]
    description: str
    kind: str                      # parameter | grade | sizes | licence
    parameter: Optional[str] = None
    lo: Optional[float] = None
    hi: Optional[float] = None
    values: List[float] = field(default_factory=list)
    grade: Optional[str] = None
    standard_lo: Optional[float] = None
    standard_hi: Optional[float] = None

    def passes(self, p: dict, relaxed: bool = False) -> Optional[bool]:
        if self.kind == "grade":
            return None if relaxed else (p.get("grade") == self.grade)
        if self.kind == "licence":
            return bool(p.get("bis_licence"))
        if self.kind == "sizes":
            sizes = p.get("sizes_mm") or p.get("sizes_mm2") or []
            return None if relaxed else all(v in sizes for v in self.values)
        v = (p.get("attributes") or {}).get(self.parameter)
        if v is None:
            return None  # unknown -> not held against the product
        lo, hi = self.lo, self.hi
        if relaxed:
            lo, hi = self.standard_lo, self.standard_hi
        if lo is not None and v < lo - 1e-9:
            return False
        if hi is not None and v > hi + 1e-9:
            return False
        return True

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


def _std_bounds(family: Optional[str], grade: Optional[str], pid: str):
    if not family:
        return None, None
    sp = ontology.standards_parameters().get(family)
    if not sp:
        return None, None
    g = grade if grade in sp["grades"] else sp.get("default_grade")
    b = sp["grades"].get(g, {}).get(pid, {})
    return b.get("min"), b.get("max")


def analyse_domain(domain: str, reqs: List[Requirement], family: Optional[str], grade: Optional[str],
                   licence_mandatory: bool, exclude_labels: Optional[set] = None) -> Optional[dict]:
    products = [p for p in catalog() if p["category"] == domain]
    if family and products:
        # compare like with like: products certified to the tender's standard (e.g. lamps vs street-light luminaires)
        from app.engine.std_refs import base_number, family_of
        exact = [p for p in products if family_of(p.get("standard", "")) == family]
        same_base = [p for p in products if base_number(family_of(p.get("standard", ""))) == base_number(family)]
        products = exact or same_base or products
    if not products:
        return None
    exclude_labels = exclude_labels or set()
    known_attrs = {k for p in products for k in (p.get("attributes") or {})}
    gates: List[Gate] = []
    if licence_mandatory:
        gates.append(Gate("LEGAL:licence", None, "Valid BIS licence (mandatory under QCO — legal gate, not a tender restriction)", "licence"))
    if grade:
        src = next((r for r in reqs if r.grade == grade), None)
        gates.append(Gate(f"GRADE:{grade}", src.clause_key if src else None, f"Grade {grade}", "grade", grade=grade))
    for r in reqs:
        if r.kind != "parameter" or r.domain != domain or not r.parameter or r.id in exclude_labels:
            continue
        if r.op != "enum" and r.parameter not in known_attrs:
            continue
        if r.op == "enum" and r.parameter in ("nominal_diameter", "conductor_area"):
            gates.append(Gate(r.id, r.clause_key, f"Sizes {', '.join(f'{v:g}' for v in r.norm.get('values', []))} {r.norm.get('unit')}",
                              "sizes", values=r.norm.get("values", [])))
            continue
        if r.op == "enum":
            continue
        slo, shi = _std_bounds(family, grade, r.parameter)
        gates.append(Gate(r.id, r.clause_key, f"{r.parameter_label}: " + r.text[:90], "parameter", parameter=r.parameter,
                          lo=r.norm.get("min"), hi=r.norm.get("max"), standard_lo=slo, standard_hi=shi))

    def eligible(active: List[Gate], relaxed_label: Optional[str] = None, drop_label: Optional[str] = None):
        out = []
        for p in products:
            ok = True
            for g in active:
                if g.label == drop_label:
                    continue
                res = g.passes(p, relaxed=(g.label == relaxed_label))
                if res is False:
                    ok = False
                    break
            if ok:
                out.append(p)
        return out

    legal = [g for g in gates if g.kind == "licence"]
    base_pool = eligible(legal)
    base_mfrs = {p["manufacturer"] for p in base_pool}
    final = eligible(gates)
    final_mfrs = {p["manufacturer"] for p in final}

    funnel = [{"step": "Market (catalogue)", "products": len(products), "manufacturers": len({p['manufacturer'] for p in products})}]
    applied: List[Gate] = []
    for g in gates:
        applied.append(g)
        e = eligible(applied)
        funnel.append({"step": g.description[:80], "clause_key": g.clause_key, "label": g.label,
                       "products": len(e), "manufacturers": len({p['manufacturer'] for p in e})})

    impacts = []
    for g in gates:
        if g.kind == "licence":
            continue
        without = eligible(gates, drop_label=g.label)
        without_m = {p["manufacturer"] for p in without}
        relaxed_m = None
        stricter = False
        if g.kind == "parameter" and (g.standard_lo is not None or g.standard_hi is not None):
            relaxed = eligible(gates, relaxed_label=g.label)
            relaxed_m = {p["manufacturer"] for p in relaxed}
            stricter = ((g.lo is not None and g.standard_lo is not None and g.lo > g.standard_lo + 1e-9) or
                        (g.hi is not None and g.standard_hi is not None and g.hi < g.standard_hi - 1e-9) or
                        (g.hi is not None and g.standard_hi is None and g.standard_lo is not None and g.kind == "parameter" and False))
        gain = len(without_m) - len(final_mfrs)
        excluded_share = (gain / len(without_m)) if without_m else 0.0
        verdict = "neutral"
        if stricter and (excluded_share >= 0.5 or (len(final_mfrs) < MIN_COMPETITION <= len(relaxed_m or without_m))):
            verdict = "restrictive"
        elif stricter and gain > 0:
            verdict = "tighter_than_standard"
        elif gain > 0 and len(final_mfrs) < MIN_COMPETITION:
            verdict = "limits_competition"
        impacts.append({
            "label": g.label, "clause_key": g.clause_key, "description": g.description, "kind": g.kind,
            "parameter": g.parameter, "tender_bounds": [g.lo, g.hi], "standard_bounds": [g.standard_lo, g.standard_hi],
            "stricter_than_standard": stricter, "manufacturers_if_removed": len(without_m),
            "manufacturers_if_relaxed_to_standard": len(relaxed_m) if relaxed_m is not None else None,
            "manufacturers_excluded_by_this_clause": gain, "excluded_share": round(excluded_share, 3), "verdict": verdict,
            "excluded_manufacturers": sorted(without_m - final_mfrs),
        })
    # restriction index is measured against the pool that is legal AND of the requested grade/class —
    # choosing a grade is a legitimate functional decision; what we measure is what the other clauses remove.
    graded = {p["manufacturer"] for p in eligible([g for g in gates if g.kind in ("licence", "grade")])}
    restriction_index = round(100 * (1 - (len(final_mfrs) / len(graded))), 1) if graded else 0.0
    return {
        "domain": domain, "standard": family, "grade": grade,
        "catalogue_note": "Synthetic demonstration catalogue (fictional manufacturers). Plug GeM / BIS licence data in production.",
        "total_products": len(products), "legal_products": len(base_pool), "legal_manufacturers": len(base_mfrs),
        "eligible_products": len(final), "eligible_manufacturers": len(final_mfrs),
        "eligible_manufacturer_names": sorted(final_mfrs), "restriction_index": restriction_index,
        "competition_ok": len(final_mfrs) >= MIN_COMPETITION, "funnel": funnel,
        "clause_impacts": sorted(impacts, key=lambda x: -x["manufacturers_excluded_by_this_clause"]),
        "excluded_contradictory_requirements": sorted(exclude_labels),
    }


def analyse(reqs: List[Requirement], domain_standards: Dict[str, dict], exclude_labels: Optional[set] = None) -> List[dict]:
    """domain_standards: {domain: {"family": "IS 1786", "grade": "Fe 500D", "licence_mandatory": True}}.
    exclude_labels: requirement ids that sit in a formal contradiction (analysed separately) — otherwise
    an impossible spec would make every clause look irrelevant."""
    out = []
    for dom, info in domain_standards.items():
        r = analyse_domain(dom, reqs, info.get("family"), info.get("grade"), info.get("licence_mandatory", False), exclude_labels)
        if r:
            out.append(r)
    return out
