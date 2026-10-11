"""
Bid / No-Bid advisor for contractors — "should I spend effort on this tender, and what must happen by when?"

Combines the deterministic Tender Match Index with the calendar:
  * substantive gaps (the offered product fails a mandatory value)      → change product or skip
  * documentary gaps with lead times (NABL tests, licence renewal)      → back-scheduled against the bid due date
  * competition context from the tender's market model                 → how many makers can realistically comply
Lead times are planning estimates (test turnaround from the parameter ontology; licence renewal as a configurable
allowance) — they are shown as such.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

from app.engine import ontology

LICENCE_RENEWAL_DAYS = 30
SAMPLE_DISPATCH_DAYS = 2
DOC_DAYS = 1


def advise(form: dict, score: dict, twin: dict, today: Optional[date] = None) -> dict:
    today = today or date.today()
    due_s = form["tender"].get("bid_due")
    due = date.fromisoformat(due_s) if due_s else None
    days_left = (due - today).days if due else None
    fields = {f["id"]: f for f in form["fields"]}
    tasks: List[dict] = []
    substantive: List[dict] = []
    for r in score["results"]:
        if r["status"] in ("MEETS", "EXCEEDS"):
            if r["type"] == "number" and r["evidence_strength"] < 2 and fields.get(r["field_id"], {}).get("knockout"):
                pid = fields[r["field_id"]].get("parameter")
                t = ontology.param_test(pid) if pid else None
                if t:
                    tasks.append({"field_id": r["field_id"], "kind": "test", "task": f"Get a NABL test report for {r['label']} ({t['standard']})",
                                  "days": int(t.get("days", 5)) + SAMPLE_DISPATCH_DAYS, "group": t.get("group")})
            continue
        f = fields.get(r["field_id"], {})
        if r["status"] in ("FAILS", "CONFLICT") and r["type"] in ("number", "sizes", "standard"):
            substantive.append({"field_id": r["field_id"], "label": r["label"], "clause_key": r["clause_key"], "detail": r["detail"]})
            continue
        if r["type"] == "certificate" and r["status"] in ("FAILS", "MISSING"):
            tasks.append({"field_id": r["field_id"], "kind": "licence", "task": r["action"] or f"Obtain/renew {r['label']}",
                          "days": LICENCE_RENEWAL_DAYS, "group": "licence"})
            continue
        if r["type"] == "test_report" and r["status"] in ("MISSING", "FAILS", "UNVERIFIED"):
            tasks.append({"field_id": r["field_id"], "kind": "test", "task": r["action"] or "Obtain a NABL type test report",
                          "days": 10 + SAMPLE_DISPATCH_DAYS, "group": "type_test"})
            continue
        if r["status"] in ("MISSING", "UNVERIFIED") and r["action"]:
            tasks.append({"field_id": r["field_id"], "kind": "document", "task": r["action"], "days": DOC_DAYS, "group": "docs"})
    # tests in the same group run once, in parallel groups
    groups: Dict[str, int] = {}
    for t in tasks:
        groups[t["group"]] = max(groups.get(t["group"], 0), t["days"])
    critical = max(groups.values()) if groups else 0
    plan = []
    for g, d in sorted(groups.items(), key=lambda kv: -kv[1]):
        members = [t for t in tasks if t["group"] == g]
        start = (due - timedelta(days=d + 1)) if due else None
        plan.append({"group": g, "days": d, "tasks": [m["task"] for m in members],
                     "start_by": start.isoformat() if start else None, "late": bool(due and start and start < today)})
    competitors = None
    for m in twin.get("market") or []:
        if m.get("domain") in (score.get("scope") or []):
            competitors = m.get("eligible_manufacturers")
    if substantive:
        verdict, tone = "NO-BID with this product", "bad"
        reason = f"{len(substantive)} mandatory value(s) are not met by the offered product — they cannot be fixed with documents. Offer a compliant model or skip."
    elif days_left is not None and critical > days_left:
        verdict, tone = "RISKY — not enough time", "warn"
        reason = f"The longest preparation path needs ~{critical} day(s) but only {days_left} day(s) remain before the bid due date."
    elif tasks:
        verdict, tone = "BID — after completing the actions", "ok"
        reason = f"All gaps are documentary; ~{critical} day(s) of preparation fit within the {days_left} day(s) left." if days_left is not None else "All gaps are documentary."
    else:
        verdict, tone = "BID — ready to submit", "good"
        reason = "Every requirement is met and evidenced."
    return {"verdict": verdict, "tone": tone, "reason": reason, "days_left": days_left, "bid_due": due_s, "critical_path_days": critical,
            "plan": plan, "substantive": substantive, "expected_competitors": competitors,
            "note": "Lead times are planning estimates (test turnaround from the parameter ontology, licence renewal allowance "
                    f"{LICENCE_RENEWAL_DAYS} days); confirm with the laboratory / BIS."}
