"""
Pre-bid Clarification Intelligence.

Predicts the questions bidders will ask *before* the tender is published — from the compiler's
findings plus institutional memory (how often the same wording produced queries in the past) —
and drafts an evidence-linked response for each. Also parses a received pre-bid Q&A document and
links every query to the clause it concerns.

Likelihood = base rate of the rule  ⊕  severity  ⊕  historical question rate of similar clauses.
All drafts are marked DRAFT and need approval; approved responses that change a clause are
propagated into a corrigendum draft (see corrigendum.fixes_to_corrigendum).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.engine.memory import Memory

BASE_RATE = {
    "SS-RES-001": 0.92, "SS-CON-001": 0.95, "SS-CON-002": 0.9, "SS-STD-003": 0.88, "SS-CON-005": 0.9, "SS-RES-003": 0.82,
    "SS-RES-004": 0.7, "SS-CON-004": 0.8, "SS-CON-003": 0.72, "SS-UNIT-001": 0.7, "SS-CERT-001": 0.6, "SS-TEST-001": 0.55,
    "SS-TEST-002": 0.55, "SS-ACC-001": 0.55, "SS-STD-001": 0.6, "SS-AMB-001": 0.45, "SS-AMB-002": 0.4, "SS-TOL-001": 0.45,
    "SS-MOD-001": 0.4, "SS-INS-001": 0.35, "SS-STD-006": 0.3, "SS-CMP-001": 0.25,
}
SEV_BOOST = {"critical": 0.06, "major": 0.03, "minor": 0.0, "info": -0.1}


def _question(f: dict) -> Optional[str]:
    rid, k, msg = f["rule_id"], f.get("clause_key"), f["message"]
    q = f.get("quote") or ""
    if rid == "SS-RES-001":
        return f"Clause {k} names specific brands. Will material of other manufacturers conforming to the specified Indian Standard and bearing the BIS Standard Mark be accepted?"
    if rid == "SS-RES-003":
        return f"Clause {k} is stricter than the governing Indian Standard and very few manufacturers can meet it. What is the technical justification? Can the limit be aligned with the standard?"
    if rid == "SS-RES-004":
        return "The combined specification appears to be met by very few manufacturers. Will the department review the restrictive parameters to enable wider participation?"
    if rid in ("SS-CON-001",):
        clauses = ", ".join(sorted({a.get("clause_key") for e in f.get("evidence", []) for a in e.get("core", []) if a.get("clause_key")})) or k
        return f"Clauses {clauses} appear to be mutually contradictory — no product can satisfy all of them. Which requirement will prevail?"
    if rid == "SS-CON-002":
        return f"Clause {k} conflicts with the Indian Standard cited in the tender. Which one governs technical evaluation?"
    if rid == "SS-CON-003":
        return f"Clause {k} states a limit weaker than the cited standard/grade. Should bidders follow the standard or the clause?"
    if rid == "SS-STD-003":
        return f"Clause {k} cites a withdrawn/superseded standard. Shall bidders quote material conforming to the current standard instead?"
    if rid == "SS-CON-005":
        return f"Clause {k} requires testing before dispatch that takes longer than the delivery period. Will manufacturer's test certificates be accepted, or will the delivery period be extended?"
    if rid == "SS-CON-004":
        return "The pre-bid meeting / bid schedule appears inconsistent. Please confirm the revised dates."
    if rid == "SS-UNIT-001":
        return f"Please confirm the unit of the value specified in Clause {k}."
    if rid == "SS-CERT-001":
        return "Is a valid BIS licence mandatory for the offered material, and should a copy be submitted with the technical bid?"
    if rid == "SS-TEST-001":
        return f"Which test method will be followed for the parameters in Clause {k}? Are manufacturer's test certificates acceptable?"
    if rid == "SS-TEST-002":
        return "Are manufacturer's in-house test certificates acceptable, or are reports from a NABL-accredited laboratory required?"
    if rid == "SS-ACC-001":
        return "What is the sampling plan and the criteria for acceptance / rejection of a lot?"
    if rid == "SS-STD-001":
        return f"Clause {k} refers to 'relevant IS codes'. Please specify the exact standard(s) and clauses applicable."
    if rid == "SS-AMB-001":
        return f"Clause {k} uses “{q}”. How will this be evaluated? Please state measurable criteria."
    if rid == "SS-AMB-002":
        return f"Clause {k} says “{q}”. Please define the exact requirement/frequency."
    if rid == "SS-TOL-001":
        return f"What tolerance applies to the dimensions in Clause {k}?"
    if rid == "SS-MOD-001":
        return f"Clause {k} uses 'should/may'. Is this requirement mandatory?"
    if rid == "SS-INS-001":
        return "At which stage will inspection be carried out and who bears the testing cost?"
    return None


def _draft_response(f: dict) -> str:
    fix = f.get("fix") or {}
    if fix.get("op") in ("replace", "replace_clause", "append", "add_clause", "delete_clause"):
        return (f"DRAFT: The clause will be amended through a corrigendum. Proposed wording/action: {f.get('suggestion')} "
                f"(Basis: {f.get('basis') or 'technical review'}).")
    return f"DRAFT: {f.get('suggestion') or 'Clarification to be provided by the technical committee.'}"


def predict(twin: dict, memory: Optional[Memory] = None, limit: int = 15) -> List[dict]:
    memory = memory or Memory()
    clauses = {c["key"]: c for c in twin.get("clauses", [])}
    out = []
    seen = set()
    for f in twin.get("findings", []):
        if f.get("review_status") in ("dismissed",):
            continue
        q = _question(f)
        if not q:
            continue
        key = (f["rule_id"], f.get("clause_key"))
        if key in seen:
            continue
        seen.add(key)
        base = BASE_RATE.get(f["rule_id"], 0.3) + SEV_BOOST.get(f["severity"], 0)
        precedents = []
        hist = 0.0
        ctext = clauses.get(f.get("clause_key") or "", {}).get("text", "")
        if ctext:
            precedents = [p for p in memory.clause_precedents(ctext, k=2) if p["prebid_questions"]]
            if precedents:
                hist = min(0.12, 0.04 * len(precedents) + 0.08 * precedents[0]["score"])
        rate = memory.question_rate(f["rule_id"])
        likelihood = max(0.05, min(0.97, 0.85 * base + hist + 0.04 * rate))
        out.append({
            "id": f"PQ-{f['fingerprint'][:8]}", "clause_key": f.get("clause_key"), "rule_id": f["rule_id"], "severity": f["severity"],
            "question": q, "likelihood": round(likelihood, 2),
            "rationale": f"{f['rule_name']}: {f['message'][:180]}" + (f" | {len(precedents)} similar historical clause(s) drew pre-bid queries." if precedents else ""),
            "draft_response": _draft_response(f), "finding_fingerprint": f["fingerprint"],
            "evidence": f.get("evidence", [])[:2], "precedents": precedents, "status": "predicted",
        })
    out.sort(key=lambda x: -x["likelihood"])
    return out[:limit]


QA_SPLIT = re.compile(r"(?im)^\s*(?:Q(?:uery)?\s*(?:No\.?)?\s*(\d+)|(\d+)\s*[.)])\s*[:.\-]?\s*")


def parse_prebid_document(text: str) -> List[dict]:
    """Parse a received pre-bid Q&A document into [{no, clause_key, question, reply}]."""
    parts = QA_SPLIT.split(text or "")
    items = []
    for i in range(1, len(parts) - 2, 3):
        no = parts[i] or parts[i + 1]
        body = parts[i + 2].strip()
        m = re.split(r"(?i)\b(?:reply|response|answer|clarification)\s*[:\-]", body, maxsplit=1)
        question = m[0].strip()
        reply = m[1].strip() if len(m) > 1 else None
        ck = re.search(r"(?:Clause|Cl\.?)\s*(\d{1,2}(?:\.\d{1,3}){0,3})", question, re.I)
        items.append({"no": int(no) if no and no.isdigit() else len(items) + 1, "clause_key": ck.group(1) if ck else None,
                      "question": question, "reply": reply})
    return items
