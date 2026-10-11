"""Tender lifecycle after publication: contractor queries, bid/no-bid advice, sealed financial opening, evaluation, award, dashboards."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.engine import bidform
from app.engine.advisor import advise
from app.engine.evaluation import evaluate
from app.models import Bid, PrebidItem, Tender
from app.services import ledger_service, studio_service, tender_service

STAGES = ["draft", "published", "bids_closed", "financial_opened", "awarded"]
STAGE_LABEL = {"draft": "Draft — under technical vetting", "published": "Published — bidding open", "bids_closed": "Bidding closed — technical evaluation",
               "financial_opened": "Financial bids opened", "awarded": "Awarded"}

_WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)*")
_STOP = set("the a an of to in is for and or be will please clarify whether can we our are this that it with as on by at from any may should shall".split())


def _toks(s: str) -> set:
    return {w for w in _WORD.findall((s or "").lower()) if w not in _STOP and len(w) > 1}


def _jacc(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def stage_of(t: Tender, today: Optional[date] = None) -> str:
    today = today or date.today()
    aw = t.award or {}
    if aw.get("decision"):
        return "awarded"
    if aw.get("financial_open"):
        return "financial_opened"
    if t.status == "published":
        due = ((t.twin or {}).get("tender") or {}).get("dates", {}).get("bid_due")
        if aw.get("bids_closed") or (due and date.fromisoformat(due) < today):
            return "bids_closed"
        return "published"
    if t.status == "awarded":
        return "awarded"
    return "draft"


# ----------------------------------------------------------------------------------------- queries
def _locate_clause(twin: dict, question: str, hint: Optional[str]) -> Optional[str]:
    keys = {c["key"] for c in twin.get("clauses", [])}
    if hint and hint in keys:
        return hint
    m = re.search(r"(?:clause|cl\.?|para|section)\s*([0-9]+(?:\.[0-9]+)*)", question, re.I)
    if m and m.group(1) in keys:
        return m.group(1)
    q = _toks(question)
    best, score = None, 0.0
    for c in twin.get("clauses", []):
        s = _jacc(q, _toks(c.get("text", "")[:600]))
        if s > score:
            best, score = c["key"], s
    return best if score >= 0.08 else None


async def raise_query(db: AsyncSession, tender_id: str, bidder: str, question: str, clause_key: Optional[str]) -> dict:
    t = await db.get(Tender, tender_id)
    if t is None:
        raise ValueError("tender not found")
    twin = t.twin or await tender_service.compile_tender(db, tender_id, reason="query")
    key = _locate_clause(twin, question, clause_key)
    rows = (await db.execute(select(PrebidItem).where(PrebidItem.tender_id == tender_id))).scalars().all()
    q = _toks(question)
    dup = None
    for r in rows:
        if r.source == "received" and _jacc(q, _toks(r.question)) >= 0.55:
            dup = r
            break
    # draft reply: a predicted question on the same clause (the compiler already knew), else a finding on that clause
    matched, draft = None, None
    preds = [p for p in twin.get("prebid", []) if p.get("clause_key") == key] if key else []
    if preds:
        matched = max(preds, key=lambda p: _jacc(q, _toks(p["question"])))
        draft = matched.get("draft_response")
    if not draft and key:
        fs = [f for f in twin.get("findings", []) if f.get("clause_key") == key]
        if fs:
            draft = f"DRAFT: {fs[0].get('suggestion') or fs[0].get('message')} (Basis: {fs[0].get('basis') or fs[0].get('rule_id')})."
    if not draft:
        clause = next((c for c in twin.get("clauses", []) if c["key"] == key), None)
        draft = ("DRAFT: The requirement stands as written in Clause " + key + ": \"" + clause["text"][:220] + "\"") if clause else \
            "DRAFT: Clarification to be provided by the technical committee."
    n = 1 + len([r for r in rows if r.source == "received"])
    qid = f"CQ-{n:03d}"
    item = PrebidItem(tender_id=tender_id, qid=qid, source="received", clause_key=key, question=question.strip()[:2000],
                      draft_response=draft, status="received",
                      data={"from": bidder, "channel": "portal", "duplicate_of": dup.qid if dup else None,
                            "predicted_id": matched["id"] if matched else None, "raised_at": datetime.utcnow().isoformat(timespec="seconds")})
    db.add(item)
    await db.commit()
    await ledger_service.append(db, bidder, "query.raised", "tender", tender_id, {"qid": qid, "clause_key": key, "question": question[:300]})
    await tender_service.compile_tender(db, tender_id, actor="system", reason=f"contractor query {qid}")
    return query_dict(item) | {"predicted": bool(matched)}


def query_dict(r: PrebidItem) -> dict:
    d = r.data or {}
    return {"qid": r.qid, "clause_key": r.clause_key, "question": r.question, "draft_response": r.draft_response, "final_response": r.final_response,
            "status": r.status, "from": d.get("from"), "duplicate_of": d.get("duplicate_of"), "predicted_id": d.get("predicted_id"),
            "raised_at": d.get("raised_at") or (r.created_at.isoformat(timespec="seconds") if r.created_at else None)}


async def list_queries(db: AsyncSession, tender_id: str, public_only: bool = False) -> List[dict]:
    rows = (await db.execute(select(PrebidItem).where(PrebidItem.tender_id == tender_id, PrebidItem.source == "received")
                             .order_by(PrebidItem.created_at))).scalars().all()
    out = [query_dict(r) for r in rows]
    if public_only:
        out = [{k: v for k, v in q.items() if k not in ("from", "draft_response")} for q in out if q["status"] in ("approved", "published")]
    return out


async def answer_query(db: AsyncSession, tender_id: str, qid: str, response: str, status: str, officer: str) -> dict:
    r = (await db.execute(select(PrebidItem).where(PrebidItem.tender_id == tender_id, PrebidItem.qid == qid))).scalars().first()
    if r is None:
        raise ValueError("query not found")
    r.final_response = response
    r.status = status
    await db.commit()
    await ledger_service.append(db, officer, "query.answered", "tender", tender_id, {"qid": qid, "status": status, "response": response[:500]})
    return query_dict(r)


# ----------------------------------------------------------------------------------------- advice
async def advice(db: AsyncSession, tender_id: str, answers: dict, scope: Optional[List[str]], today: Optional[date] = None) -> dict:
    t, form = await studio_service.form_for(db, tender_id)
    sc = bidform.score(form, answers or {}, scope=scope)
    return {"score": {k: sc[k] for k in ("match_index", "tier", "knockouts")}, **advise(form, sc, t.twin or {}, today)}


# ----------------------------------------------------------------------------------------- evaluation
def _bid_rows(bids: List[Bid]) -> List[dict]:
    out = []
    for b in bids:
        f = b.form or {}
        out.append({"bid_id": b.id, "bidder": b.bidder, "score": f.get("score") or {}, "scope": f.get("scope"), "financial": f.get("financial"),
                    "declarations": f.get("declarations") or {}, "commitment": f.get("commitment"), "salt": f.get("salt")})
    return out


async def evaluation(db: AsyncSession, tender_id: str) -> dict:
    t = await db.get(Tender, tender_id)
    if t is None:
        raise ValueError("tender not found")
    bids = (await db.execute(select(Bid).where(Bid.tender_id == tender_id).order_by(Bid.created_at))).scalars().all()
    aw = t.award or {}
    ev = evaluate(t.twin or {}, t.generation, _bid_rows(bids), financial_open=bool(aw.get("financial_open")))
    ev["stage"] = stage_of(t)
    ev["stage_label"] = STAGE_LABEL[ev["stage"]]
    ev["award"] = aw.get("decision")
    ev["opened_at"] = aw.get("opened_at")
    ev["tender"] = {"id": t.id, "title": t.title, "reference_no": t.reference_no, "organisation": t.organisation}
    ev["bids_received"] = len(bids)
    return ev


async def close_bidding(db: AsyncSession, tender_id: str, officer: str) -> dict:
    t = await db.get(Tender, tender_id)
    t.award = {**(t.award or {}), "bids_closed": True, "closed_at": datetime.utcnow().isoformat(timespec="seconds")}
    flag_modified(t, "award")
    await db.commit()
    await ledger_service.append(db, officer, "tender.bids_closed", "tender", tender_id, {})
    return await evaluation(db, tender_id)


async def open_financial(db: AsyncSession, tender_id: str, officer: str) -> dict:
    t = await db.get(Tender, tender_id)
    if t is None:
        raise ValueError("tender not found")
    bids = (await db.execute(select(Bid).where(Bid.tender_id == tender_id))).scalars().all()
    ev = evaluate(t.twin or {}, t.generation, _bid_rows(bids), financial_open=True)
    t.award = {**(t.award or {}), "bids_closed": True, "financial_open": True, "opened_at": datetime.utcnow().isoformat(timespec="seconds"),
               "opened_by": officer}
    flag_modified(t, "award")
    await db.commit()
    await ledger_service.append(db, officer, "tender.financial_opened", "tender", tender_id, {
        "integrity": ev["integrity"], "l1": {str(l["index"]): (l.get("l1") or {}).get("bidder") for l in ev["lines"]}})
    return await evaluation(db, tender_id)


async def award(db: AsyncSession, tender_id: str, officer: str, remarks: Optional[str]) -> dict:
    t = await db.get(Tender, tender_id)
    if t is None:
        raise ValueError("tender not found")
    if not (t.award or {}).get("financial_open"):
        raise PermissionError("Open the financial bids before recording an award.")
    ev = await evaluation(db, tender_id)
    decision = {"decided_by": officer, "decided_at": datetime.utcnow().isoformat(timespec="seconds"), "remarks": remarks,
                "contract_value": ev["recommended_contract_value"],
                "allocation": [{"line": l["index"], "label": l["label"], **a} for l in ev["lines"] for a in l["allocation"]]}
    t.award = {**(t.award or {}), "decision": decision}
    flag_modified(t, "award")
    t.status = "awarded"
    await db.commit()
    await ledger_service.append(db, officer, "tender.awarded", "tender", tender_id, decision)
    return await evaluation(db, tender_id)


# ----------------------------------------------------------------------------------------- dashboards
def _items(t: Tender) -> List[dict]:
    if t.generation:
        return [{"label": l["item_label"], "quantity": l["quantity"], "unit": l["unit"]} for l in t.generation.get("lines", [])]
    return []


def _tender_card(t: Tender, bids: int, queries_open: int, today: date) -> dict:
    tw = t.twin or {}
    dates = (tw.get("tender") or {}).get("dates", {})
    due = dates.get("bid_due")
    st = stage_of(t, today)
    fs = tw.get("findings") or []
    return {"id": t.id, "title": t.title, "reference_no": t.reference_no, "organisation": t.organisation, "stage": st, "stage_label": STAGE_LABEL[st],
            "stage_index": STAGES.index(st), "bid_due": due, "days_left": (date.fromisoformat(due) - today).days if due else None,
            "readiness": t.readiness_score, "gate": t.gate, "bids": bids, "queries_open": queries_open, "items": _items(t),
            "blockers": len([f for f in fs if f.get("severity") in ("blocker", "critical") and f.get("review_status") not in ("dismissed", "fixed")]),
            "generated": bool(t.generation), "contract_value": ((t.award or {}).get("decision") or {}).get("contract_value"),
            "updated_at": t.updated_at.isoformat(timespec="seconds") if t.updated_at else None}


async def officer_dashboard(db: AsyncSession, today: Optional[date] = None) -> dict:
    today = today or date.today()
    ts = (await db.execute(select(Tender).where(Tender.status.notin_(["template", "archived"])).order_by(Tender.updated_at.desc()))).scalars().all()
    bid_counts = dict((await db.execute(select(Bid.tender_id, func.count(Bid.id)).group_by(Bid.tender_id))).all())
    q_open = dict((await db.execute(select(PrebidItem.tender_id, func.count(PrebidItem.id))
                                    .where(PrebidItem.source == "received", PrebidItem.status == "received").group_by(PrebidItem.tender_id))).all())
    cards = [_tender_card(t, bid_counts.get(t.id, 0), q_open.get(t.id, 0), today) for t in ts]
    actions = []
    for c in cards:
        if c["stage"] == "draft" and c["blockers"]:
            actions.append({"tender_id": c["id"], "kind": "fix", "text": f"{c['blockers']} blocking issue(s) must be fixed before publication", "title": c["title"]})
        elif c["stage"] == "draft":
            actions.append({"tender_id": c["id"], "kind": "publish", "text": "Vetted — ready for approval and publication", "title": c["title"]})
        if c["queries_open"]:
            actions.append({"tender_id": c["id"], "kind": "queries", "text": f"{c['queries_open']} bidder quer{'y' if c['queries_open'] == 1 else 'ies'} awaiting reply", "title": c["title"]})
        if c["stage"] == "bids_closed" or (c["stage"] == "published" and c["bids"] and c["days_left"] is not None and c["days_left"] < 0):
            actions.append({"tender_id": c["id"], "kind": "evaluate", "text": f"{c['bids']} bid(s) ready for evaluation", "title": c["title"]})
        if c["stage"] == "financial_opened":
            actions.append({"tender_id": c["id"], "kind": "award", "text": "Financial bids opened — record the committee decision", "title": c["title"]})
    counts = {s: len([c for c in cards if c["stage"] == s]) for s in STAGES}
    awarded_value = sum(c["contract_value"] or 0 for c in cards)
    return {"counts": counts, "total": len(cards), "tenders": cards, "actions": actions[:20], "awarded_value": awarded_value,
            "bids_total": sum(bid_counts.values()), "queries_open": sum(q_open.values())}


async def contractor_dashboard(db: AsyncSession, bidder: Optional[str], today: Optional[date] = None) -> dict:
    today = today or date.today()
    ts = (await db.execute(select(Tender).where(Tender.status.in_(["published", "awarded"])).order_by(Tender.created_at.desc()))).scalars().all()
    bid_counts = dict((await db.execute(select(Bid.tender_id, func.count(Bid.id)).group_by(Bid.tender_id))).all())
    open_cards = [_tender_card(t, bid_counts.get(t.id, 0), 0, today) for t in ts]
    mine = []
    if bidder:
        rows = (await db.execute(select(Bid).where(func.lower(Bid.bidder) == bidder.lower()).order_by(Bid.created_at.desc()))).scalars().all()
        by_t = {t.id: t for t in ts}
        for b in rows:
            t = by_t.get(b.tender_id) or await db.get(Tender, b.tender_id)
            st = stage_of(t, today) if t else "draft"
            dec = ((t.award or {}).get("decision") or {}) if t else {}
            won = [a for a in dec.get("allocation", []) if a.get("bid_id") == b.id]
            sc = (b.form or {}).get("score") or {}
            mine.append({"bid_id": b.id, "tender_id": b.tender_id, "tender_title": t.title if t else None, "reference_no": t.reference_no if t else None,
                         "product_name": b.product_name, "match_index": b.match_index, "tier": sc.get("tier"), "knockouts": sc.get("knockouts"),
                         "sealed": bool((b.form or {}).get("commitment")), "commitment": (b.form or {}).get("commitment"),
                         "stage": st, "stage_label": STAGE_LABEL[st], "submitted_at": b.created_at.isoformat(timespec="seconds") if b.created_at else None,
                         "result": ("awarded" if won else "not awarded") if st == "awarded" else None,
                         "awarded": [{"label": a["label"], "quantity": a["quantity"], "unit_price": a["unit_price"], "value": a["value"]} for a in won]})
    return {"bidder": bidder, "open": [c for c in open_cards if c["stage"] == "published"], "closed": [c for c in open_cards if c["stage"] != "published"],
            "bids": mine}


async def stats(db: AsyncSession) -> dict:
    from app.models import LedgerEntry, Regulation, Standard
    kg = await studio_service.kg_for(db)
    ts = (await db.execute(select(Tender))).scalars().all()
    return {"tenders": len([t for t in ts if t.status not in ("template", "archived")]),
            "published": len([t for t in ts if t.status in ("published", "awarded")]),
            "awarded": len([t for t in ts if (t.award or {}).get("decision")]),
            "bids": (await db.execute(select(func.count(Bid.id)))).scalar() or 0,
            "standards": (await db.execute(select(func.count(Standard.id)))).scalar() or 0,
            "regulations": (await db.execute(select(func.count(Regulation.id)))).scalar() or 0,
            "kg_nodes": kg.g.number_of_nodes(), "kg_edges": kg.g.number_of_edges(),
            "ledger_entries": (await db.execute(select(func.count(LedgerEntry.seq)))).scalar() or 0}
