"""
Standards Equivalence Engine — parameter-by-parameter comparison of two standards/grades.

It deliberately never outputs "equivalent: yes". It outputs a *coverage profile*:
  - parameters where B is at least as strict as A      (B ⊇ A's assurance on that property)
  - parameters where B is looser                       (gap)
  - parameters only one of them controls               (unknown / not assured)
  - different test methods                             (results may not be comparable)
  - regulatory implication                             (a foreign standard never satisfies a QCO)
and a verdict band: NOT_EQUIVALENT / PARTIALLY_COMPARABLE / TECHNICALLY_COMPARABLE — always marked
"AI analysis — requires approval by the competent technical authority".
"""
from __future__ import annotations

from typing import Dict, Optional

from app.engine import ontology
from app.engine.kb import KnowledgeBase


def _strictness(pid: str, a: dict, b: dict) -> str:
    """Is B at least as strict as A for this parameter?"""
    res = []
    if a.get("min") is not None:
        if b.get("min") is None:
            res.append("looser")
        else:
            res.append("stricter" if b["min"] > a["min"] + 1e-9 else ("equal" if abs(b["min"] - a["min"]) < 1e-9 else "looser"))
    if a.get("max") is not None:
        if b.get("max") is None:
            res.append("looser")
        else:
            res.append("stricter" if b["max"] < a["max"] - 1e-9 else ("equal" if abs(b["max"] - a["max"]) < 1e-9 else "looser"))
    if "looser" in res:
        return "looser"
    if "stricter" in res:
        return "stricter"
    return "equal"


def compare(fam_a: str, fam_b: str, grade_a: Optional[str] = None, grade_b: Optional[str] = None,
            kb: Optional[KnowledgeBase] = None) -> Dict:
    sp = ontology.standards_parameters()
    A, B = sp.get(fam_a), sp.get(fam_b)
    if not A or not B:
        missing = [f for f, x in ((fam_a, A), (fam_b, B)) if not x]
        return {"error": f"No machine-readable requirement set for {', '.join(missing)}.", "available": sorted(sp)}
    ga = grade_a if grade_a in A["grades"] else A["default_grade"]
    gb = grade_b if grade_b in B["grades"] else B["default_grade"]
    pa, pb = A["grades"][ga], B["grades"][gb]
    rows = []
    for pid in sorted(set(pa) | set(pb), key=lambda p: ontology.param_label(p)):
        ra, rb = pa.get(pid), pb.get(pid)
        if ra and rb:
            rel = _strictness(pid, ra, rb)
        elif ra:
            rel = "not_controlled_by_b"
        else:
            rel = "only_in_b"
        rows.append({"parameter": pid, "label": ontology.param_label(pid), "unit": ontology.param_unit(pid), "a": ra, "b": rb, "b_vs_a": rel})
    covered = [r for r in rows if r["b_vs_a"] in ("equal", "stricter")]
    gaps = [r for r in rows if r["b_vs_a"] in ("looser", "not_controlled_by_b")]
    both = [r for r in rows if r["a"] and r["b"]]
    a_params = [r for r in rows if r["a"]]
    coverage = round(len(covered) / len(a_params), 3) if a_params else 0.0
    tm_rows = []
    for k in sorted(set(A.get("test_methods", {})) | set(B.get("test_methods", {}))):
        ta, tb = A.get("test_methods", {}).get(k), B.get("test_methods", {}).get(k)
        tm_rows.append({"property": k, "a": ta, "b": tb, "same": bool(ta and tb and ta == tb)})
    if coverage >= 0.9 and not gaps:
        verdict = "TECHNICALLY_COMPARABLE"
    elif coverage >= 0.3:
        verdict = "PARTIALLY_COMPARABLE"
    else:
        verdict = "NOT_EQUIVALENT"
    reg_note = None
    if kb is not None:
        regs_a = kb.regulations_for_family(fam_a)
        regs_b = kb.regulations_for_family(fam_b)
        if regs_a and not regs_b:
            reg_note = (f"{fam_a} is mandated by {regs_a[0].title}. A product certified only to {fam_b} cannot be sold in India "
                        f"for this use without a BIS licence to {fam_a} — technical comparability does NOT create legal substitutability.")
    return {
        "a": {"family": fam_a, "grade": ga, "title": A["title"], "body": A["body"], "edition": A.get("edition")},
        "b": {"family": fam_b, "grade": gb, "title": B["title"], "body": B["body"], "edition": B.get("edition")},
        "parameters": rows, "coverage_of_a_by_b": coverage,
        "summary": {"compared": len(both), "b_at_least_as_strict": len(covered), "gaps": len(gaps),
                    "only_in_b": len([r for r in rows if r["b_vs_a"] == "only_in_b"])},
        "test_methods": tm_rows,
        "test_method_note": "Different test methods can yield non-comparable results even for identical limits." if any(not t["same"] for t in tm_rows) else None,
        "regulatory_implication": reg_note,
        "verdict": verdict,
        "decision_status": "AI_ANALYSIS_PENDING_HUMAN_APPROVAL",
        "disclaimer": "AI-assisted technical comparison from curated parameter sets. Not an equivalence determination. "
                      "Requires approval by the competent technical authority (e.g. BIS technical committee / tender committee).",
    }


def available() -> Dict:
    sp = ontology.standards_parameters()
    return {k: {"title": v["title"], "body": v["body"], "grades": list(v["grades"]), "domain": v["domain"]} for k, v in sp.items()}
