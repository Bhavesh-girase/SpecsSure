"""
Contractor Bid Mirror — shows a bidder their bid the way the technical evaluator will see it.

For every requirement of the (canonical) tender twin it finds supporting evidence in the bidder's
documents, evaluates it *deterministically* against the normalised requirement bounds and assigns:

  COMPLIANT               strongest evidence (lab report / licence) satisfies the requirement
  CLAIMED_ONLY            only a manufacturer claim (datasheet) supports it — evaluator may ask for proof
  NON_COMPLIANT           evidence violates the requirement (with the numbers)
  CONFLICTING_EVIDENCE    documents disagree with each other (e.g. datasheet vs lab report)
  MISSING_EVIDENCE        nothing in the bid addresses it
  NEEDS_CLARIFICATION     the requirement itself is contradictory/ambiguous — ask in pre-bid
  DECLARATION             an undertaking (delivery, warranty…) the bidder must sign

Output = traceable compliance matrix (every row → document, page, snippet) + an evaluator-style
verdict + the list of documents to obtain and questions to raise.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from app.engine import ontology
from app.engine.std_refs import base_number

STATUS_ORDER = ["NON_COMPLIANT", "CONFLICTING_EVIDENCE", "MISSING_EVIDENCE", "NEEDS_CLARIFICATION", "CLAIMED_ONLY", "DECLARATION", "COMPLIANT"]
BLOCKING = {"NON_COMPLIANT", "CONFLICTING_EVIDENCE", "MISSING_EVIDENCE"}


def _satisfies(req: dict, ev: dict) -> Optional[bool]:
    lo, hi = req["norm"].get("min"), req["norm"].get("max")
    v = ev.get("value")
    if v is None:
        return None
    q = ev.get("qualifier")
    # a guaranteed 'max' claim satisfies an upper bound only if claim <= bound; 'min' claim satisfies a lower bound if claim >= bound
    if lo is not None and v < lo - 1e-9:
        return False
    if hi is not None and v > hi + 1e-9:
        if q == "min":      # "≥ X" claim says nothing about the upper bound
            return None
        return False
    if hi is not None and q == "min":
        return None
    if lo is not None and q == "max":
        return None
    return True


def _fmt_req(req: dict) -> str:
    lo, hi, u = req["norm"].get("min"), req["norm"].get("max"), req["norm"].get("unit", "")
    u = "" if u in ("dimensionless",) else u.replace("**2", "²").replace("percent", "%")
    if lo is not None and hi is not None and lo == hi:
        return f"= {lo:g} {u}"
    if lo is not None and hi is not None:
        return f"{lo:g}–{hi:g} {u}"
    if lo is not None:
        return f"≥ {lo:g} {u}"
    if hi is not None:
        return f"≤ {hi:g} {u}"
    return ""


def mirror(twin: dict, evidence_docs: List[dict], bid_due: Optional[str] = None, bidder: str = "Bidder",
           scope_domains: Optional[List[str]] = None) -> Dict:
    items = [dict(i) for d in evidence_docs for i in d["items"]]
    metas = [d["meta"] for d in evidence_docs]
    bid_due = bid_due or twin["tender"].get("dates", {}).get("bid_due")
    clause_issues: Dict[str, List[dict]] = {}
    for f in twin.get("findings", []):
        if f["rule_id"] in ("SS-CON-001", "SS-CON-002", "SS-UNIT-001", "SS-AMB-002", "SS-STD-001") and f.get("clause_key"):
            clause_issues.setdefault(f["clause_key"], []).append(f)
    rows: List[dict] = []
    not_tested = {p for m in metas for p in m.get("not_tested_parameters", [])}
    bid_domains = set(scope_domains or [d for m in metas for d in m.get("domains", [])])
    clause_text = {c["key"]: c["heading"] + " " + c["text"] for c in twin.get("clauses", [])}
    out_of_scope = []

    for req in twin["requirements"]:
        kind = req["kind"]
        if bid_domains:
            doms = [req["domain"]] if req.get("domain") and req["domain"] != "general" else ontology.detect_domains(req["text"]) or ontology.detect_domains(clause_text.get(req["clause_key"], ""))
            if doms and not (set(doms) & bid_domains):
                out_of_scope.append(req["id"])
                continue
        if kind == "schedule":
            continue
        if kind == "parameter" and ontology.parameters().get(req.get("parameter") or "", {}).get("category") in ("delivery", "warranty", "packaging"):
            kind = "declaration_param"
        row = {"requirement_id": req["id"], "clause_key": req["clause_key"], "page": req["page"], "kind": req["kind"],
               "requirement": req["text"], "parameter": req.get("parameter_label"),
               "required": _fmt_req(req) if kind in ("parameter", "declaration_param") else None,
               "evidence": [], "status": None, "explanation": "", "evidence_strength": 0}
        issues = [f for f in clause_issues.get(req["clause_key"], []) if not f.get("requirement_ids") or req["id"] in f.get("requirement_ids", [])]
        if kind == "parameter" and req.get("parameter"):
            pid = req["parameter"]
            if req["op"] == "enum":
                sizes = [i for i in items if i["kind"] == "sizes" and i["parameter"] == pid]
                need = set(req["norm"].get("values") or [])
                if not sizes:
                    row.update(status="MISSING_EVIDENCE", explanation=f"No document lists the offered sizes; required {sorted(need)}.")
                else:
                    best = max(sizes, key=lambda i: i["strength"])
                    missing = sorted(need - set(best["values"]))
                    row["evidence"] = sizes
                    row["evidence_strength"] = best["strength"]
                    row.update(status="NON_COMPLIANT" if missing else ("COMPLIANT" if best["strength"] >= 2 else "CLAIMED_ONLY"),
                               explanation=f"Missing sizes {missing}." if missing else f"All required sizes {sorted(need)} are covered.")
                rows.append(row)
                continue
            evs = [i for i in items if i["kind"] == "parameter" and i["parameter"] == pid]
            row["evidence"] = evs
            if issues and any(f["rule_id"] in ("SS-CON-001", "SS-CON-002") for f in issues):
                row.update(status="NEEDS_CLARIFICATION",
                           explanation="The tender requirement itself is contradictory (formally proven by SpecSure) — raise a pre-bid query before quoting. "
                                       + issues[0]["message"][:160])
                rows.append(row)
                continue
            if not evs:
                extra = " The lab report explicitly states it was not tested." if pid in not_tested else ""
                row.update(status="MISSING_EVIDENCE", explanation=f"No document states {req.get('parameter_label')}.{extra}")
                rows.append(row)
                continue
            verdicts = [(e, _satisfies(req, e)) for e in evs]
            strong = [(e, v) for e, v in verdicts if e["strength"] >= 2 and v is not None]
            weak = [(e, v) for e, v in verdicts if e["strength"] < 2 and v is not None]
            row["evidence_strength"] = max(e["strength"] for e in evs)
            fails = [(e, v) for e, v in verdicts if v is False]
            passes = [(e, v) for e, v in verdicts if v is True]
            if fails and passes:
                e_f = fails[0][0]
                e_p = passes[0][0]
                status = "NON_COMPLIANT" if any(e["strength"] >= 2 for e, _ in fails) else "CONFLICTING_EVIDENCE"
                row.update(status=status, explanation=f"{e_f['doc_name']} (p.{e_f['page']}) shows {e_f['raw_value']} which violates {row['required']}, "
                                                      f"while {e_p['doc_name']} shows {e_p['raw_value']}.")
            elif fails:
                e_f = max((e for e, _ in fails), key=lambda e: e["strength"])
                row.update(status="NON_COMPLIANT", explanation=f"{e_f['doc_name']} (p.{e_f['page']}) states {e_f['raw_value']} — requirement is {row['required']}.")
            elif strong and all(v for _, v in strong):
                e = max((e for e, _ in strong), key=lambda e: e["strength"])
                row.update(status="COMPLIANT", explanation=f"Verified by {e['doc_type'].replace('_', ' ')} {e['doc_name']} (p.{e['page']}): {e['raw_value']}.")
            elif weak and all(v for _, v in weak):
                e = weak[0][0]
                row.update(status="CLAIMED_ONLY", explanation=f"Only a manufacturer claim ({e['doc_name']}, p.{e['page']}: {e['raw_value']}). Attach a NABL test report to prove it.")
            else:
                row.update(status="MISSING_EVIDENCE", explanation="Evidence found but it does not state a comparable value (e.g. only 'min' given for an upper limit).")
            if issues and row["status"] == "COMPLIANT":
                row["explanation"] += f" Note: clause has an open issue ({issues[0]['rule_id']})."
            rows.append(row)
            continue

        if kind in ("standard_compliance", "certification") or (kind == "packaging" and "certification" in req.get("tags", [])):
            fams = [s["family"] for s in req.get("standards", []) if s.get("body") == "BIS"]
            gov = (req.get("links") or {}).get("governing_standard")
            target = fams[0] if fams else (gov and gov.split(":")[0])
            std_evs = [i for i in items if i["kind"] == "standard" and (not target or base_number(i["extra"].get("family", "")) == base_number(target)
                                                                             or i["extra"].get("family") == target)]
            row["evidence"] = std_evs
            if issues:
                row.update(status="NEEDS_CLARIFICATION", explanation=issues[0]["message"][:200])
            elif not std_evs:
                row.update(status="MISSING_EVIDENCE", explanation=f"No document declares conformity to {target or 'the cited standard'}.")
            else:
                best = max(std_evs, key=lambda i: i["strength"])
                row["evidence_strength"] = best["strength"]
                row.update(status="COMPLIANT" if best["strength"] >= 2 else "CLAIMED_ONLY",
                           explanation=f"{best['doc_name']} declares {best['raw_value']}.")
            rows.append(row)
            continue
        if kind in ("delivery", "warranty", "packaging", "documentation", "inspection", "acceptance", "general", "eligibility", "declaration_param", "schedule", "brand"):
            row.update(status="DECLARATION", explanation="Undertaking / declaration to be furnished in the bid (not verifiable from product documents).")
            rows.append(row)
            continue
        if kind == "testing":
            reps = [m for m in metas if m.get("doc_type") == "test_report"]
            if not reps:
                row.update(status="MISSING_EVIDENCE", explanation="No test report attached.")
            else:
                r = reps[0]
                row["evidence"] = [{"doc_name": r["doc_name"], "page": 1, "snippet": f"{r.get('lab')} — {r.get('nabl_certificate', 'no NABL no.')} — report {r.get('report_no')} dated {r.get('report_date')}",
                                    "doc_type": "test_report", "strength": 3}]
                row["evidence_strength"] = 3
                row.update(status="COMPLIANT" if r.get("accredited") else "CLAIMED_ONLY",
                           explanation=("NABL-accredited lab report attached." if r.get("accredited") else "Test report is not from an identified accredited lab."))
            rows.append(row)
            continue

    # ---------------- mandatory certification check (QCO / CRS) --------------------------------
    cert_rows = []
    lic = next((m for m in metas if m.get("licence_no")), None)
    for dom, ds in twin.get("domain_standards", {}).items():
        if bid_domains and dom not in bid_domains:
            continue
        mand = [g for g in ds.get("regulations_in_force", []) if (g.get("is_mandatory") or "yes") == "yes"]
        if not mand:
            continue
        row = {"requirement_id": f"CERT-{dom}", "clause_key": ds.get("clause_key"), "page": None, "kind": "certification",
               "requirement": f"Valid BIS licence for {ds.get('resolved')} ({mand[0]['title']})", "parameter": "BIS licence",
               "required": f"licence valid on {bid_due}", "evidence": [], "status": None, "explanation": "", "evidence_strength": 0}
        if not lic:
            row.update(status="MISSING_EVIDENCE", explanation="No BIS licence (CM/L) found in the bid documents — mandatory under the QCO.")
        else:
            row["evidence"] = [i for i in items if i["kind"] in ("licence",)]
            row["evidence_strength"] = 2
            problems = []
            lic_std = [i for i in items if i["kind"] == "standard" and i["doc_type"] == "certificate"]
            if lic_std and base_number(lic_std[0]["extra"]["family"]) != base_number(ds["family"]):
                problems.append(f"licence is for {lic_std[0]['raw_value']}, tender requires {ds.get('resolved')}")
            if lic.get("valid_to") and bid_due and lic["valid_to"] < bid_due:
                problems.append(f"licence {lic['licence_no']} expires on {lic['valid_to']}, before the bid due date {bid_due}")
            g = ds.get("grade")
            if g and lic.get("grade") and g.replace(" ", "").lower() not in lic["grade"].replace(" ", "").lower():
                problems.append(f"licence grade {lic['grade']} ≠ required {g}")
            if lic.get("status") and not str(lic["status"]).lower().startswith("operat"):
                problems.append(f"licence status '{lic['status']}'")
            row.update(status="NON_COMPLIANT" if problems else "COMPLIANT",
                       explanation=("; ".join(problems) + ". Renew/verify on the BIS portal before submission.") if problems
                       else f"Licence {lic['licence_no']} covers {ds.get('resolved')} and is valid through the bid due date (verify online).")
        cert_rows.append(row)
    rows = cert_rows + rows

    applicable = [r for r in rows if r["status"] != "DECLARATION"]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUS_ORDER}
    score = round(100 * counts["COMPLIANT"] / len(applicable), 1) if applicable else 0.0
    blocking = [r for r in rows if r["status"] in BLOCKING]
    verdict = "LIKELY_TECHNICALLY_NON_RESPONSIVE" if any(r["status"] == "NON_COMPLIANT" for r in rows) else \
              ("AT_RISK_MISSING_EVIDENCE" if blocking else ("RESPONSIVE_SUBJECT_TO_CLARIFICATION" if counts["NEEDS_CLARIFICATION"] else "LIKELY_RESPONSIVE"))
    todo = []
    for r in rows:
        if r["status"] == "MISSING_EVIDENCE":
            todo.append(f"Obtain evidence for Clause {r['clause_key']} — {r['parameter'] or r['requirement'][:60]}")
        elif r["status"] == "CLAIMED_ONLY":
            todo.append(f"Attach NABL test report for {r['parameter'] or r['requirement'][:60]} (Clause {r['clause_key']})")
        elif r["status"] == "NON_COMPLIANT":
            todo.append(f"Resolve non-compliance on Clause {r['clause_key']}: {r['explanation'][:120]}")
    questions = [p for p in twin.get("prebid", []) if p.get("clause_key") in {r["clause_key"] for r in rows if r["status"] in ("NEEDS_CLARIFICATION", "NON_COMPLIANT")}]
    rows.sort(key=lambda r: (STATUS_ORDER.index(r["status"]) if r["status"] in STATUS_ORDER else 99))
    return {"bidder": bidder, "scope_domains": sorted(bid_domains), "out_of_scope_requirements": len(out_of_scope), "tender_title": twin["tender"].get("title"), "bid_due": bid_due, "rows": rows, "counts": counts,
            "compliance_score": score, "verdict": verdict, "action_items": todo, "suggested_prebid_questions": questions[:6],
            "documents": [{k: v for k, v in m.items()} for m in metas],
            "disclaimer": "Decision support. Final technical evaluation rests with the tender committee."}
