"""
Regulatory Change Radar + continuous revalidation ("Dependabot for tenders").

A regulatory event (new standard, revision, amendment, withdrawal, new/amended QCO) is applied to
the knowledge base, then:
  1. impact set  = standards directly changed  ∪  standards that depend on them (reverse traversal of
                   normative / test-method edges — a change to IS 1608 affects every IS 1786 tender)
  2. affected    = every active tender / template whose Digital Twin references the impact set
  3. revalidate  = re-compile each affected twin against the new KB snapshot
  4. delta       = findings introduced / resolved, gate change → notification to the tender owner

Source watchers poll official pages, hash their content and raise a 'source_changed' event for human
triage (we never auto-parse a gazette into law — a human confirms the event first).
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Dict, List, Set

from app.engine.kb import KnowledgeBase
from app.engine.std_refs import base_number, family_of

SCENARIOS: Dict[str, Dict] = {
    "amendment_is1786": {
        "label": "SIMULATED: Amendment No. 4 to IS 1786:2008 (Agt requirement revised)",
        "event_type": "amendment", "subject": "IS 1786:2008",
        "title": "SIMULATED Amendment No. 4 to IS 1786:2008",
        "summary": "Simulated demo event: revises the total elongation at maximum force (Agt) requirement for ductile grades and adds a re-bend test clarification.",
        "changed_clauses": "Table 3 (mechanical properties), Clause 8.3",
        "effective_in_days": 45,
    },
    "revision_is269": {
        "label": "SIMULATED: New edition IS 269:2026 supersedes IS 269:2015",
        "event_type": "revision", "subject": "IS 269:2015", "new_is_number": "IS 269:2026",
        "title": "SIMULATED Ordinary Portland Cement — Specification (Seventh Revision)",
        "summary": "Simulated demo event: a revised edition that will supersede IS 269:2015.",
        "effective_in_days": 20,
    },
    "qco_led": {
        "label": "SIMULATED: New QCO for LED luminaires (effective in 90 days)",
        "event_type": "qco_new", "subject": "IS 10322 (Part 5/Sec 1)",
        "title": "SIMULATED LED Luminaires (Quality Control) Order",
        "summary": "Simulated demo event: mandatory BIS certification for LED luminaires under a QCO.",
        "effective_in_days": 90,
    },
    "withdraw_is1608": {
        "label": "SIMULATED: IS 1608 (Part 1):2018 revised — test method change",
        "event_type": "amendment", "subject": "IS 1608 (Part 1):2018",
        "title": "SIMULATED Amendment No. 1 to IS 1608 (Part 1):2018",
        "summary": "Simulated demo event: tensile test method amended (strain-rate control). Product standards citing it are indirectly affected.",
        "changed_clauses": "Clause 10 (testing speed)", "effective_in_days": 30,
    },
}


def impact_set(kb: KnowledgeBase, subject: str) -> Dict[str, List[str]]:
    rec = kb.lookup(subject)
    direct = {family_of(subject)}
    dependents: Set[str] = set()
    if rec:
        frontier = [rec.id]
        seen = {rec.id}
        depth = 0
        while frontier and depth < 2:
            nxt = []
            for sid in frontier:
                for rel in kb.incoming(sid, ["normative_reference", "test_method", "safety_requirement"]):
                    if rel.from_id not in seen:
                        seen.add(rel.from_id)
                        nxt.append(rel.from_id)
                        s = kb.by_id.get(rel.from_id)
                        if s:
                            dependents.add(s.family)
            frontier = nxt
            depth += 1
    return {"direct": sorted(direct), "dependents": sorted(dependents - direct)}


def twin_families(twin: Dict) -> Set[str]:
    fams = {c["family"] for c in twin.get("citations", []) if c.get("family")}
    for ds in twin.get("domain_standards", {}).values():
        if ds.get("family"):
            fams.add(ds["family"])
        if ds.get("resolved"):
            fams.add(family_of(ds["resolved"]))
    for c in twin.get("citations", []):
        if c.get("replacement"):
            fams.add(family_of(c["replacement"]))
    return fams


def affected(twins: List[Dict], impact: Dict[str, List[str]]) -> List[Dict]:
    out = []
    direct = set(impact["direct"]) | {base_number(f) for f in impact["direct"]}
    dep = set(impact["dependents"])
    for t in twins:
        fams = twin_families(t["twin"])
        fams_b = fams | {base_number(f) for f in fams}
        hit_d = sorted(fams_b & direct)
        hit_i = sorted(fams_b & dep)
        if hit_d or hit_i:
            out.append({"tender_id": t["tender_id"], "title": t["title"], "status": t.get("status"),
                        "reason": ("directly cites/relies on " + ", ".join(hit_d)) if hit_d else ("indirectly via dependent standard(s) " + ", ".join(hit_i)),
                        "direct": bool(hit_d)})
    return out


def diff_findings(old: List[Dict], new: List[Dict]) -> Dict:
    o = {f["fingerprint"]: f for f in old}
    n = {f["fingerprint"]: f for f in new}
    return {"introduced": [n[k] for k in n if k not in o], "resolved": [o[k] for k in o if k not in n],
            "unchanged": len([k for k in n if k in o])}


def scenario_dates(key: str) -> Dict:
    s = SCENARIOS[key]
    eff = date.today() + timedelta(days=s.get("effective_in_days", 30))
    return {**s, "effective_from": eff.isoformat()}


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


WATCH_SOURCES = [
    {"key": "bis-qco-scheme-i", "url": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-i-mark-scheme/", "label": "BIS — products under compulsory certification (Scheme-I)"},
    {"key": "steel-qco", "url": "https://steel.gov.in/quality-control-orders", "label": "Ministry of Steel — Quality Control Orders"},
    {"key": "crs", "url": "https://www.crsbis.in/", "label": "BIS CRS portal"},
]
