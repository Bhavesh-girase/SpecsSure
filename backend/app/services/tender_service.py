"""
DB orchestration for the Tender Digital Twin: documents -> (corrigendum merge) -> compile -> review state
-> memory & pre-bid prediction -> persisted twin + ledger entry.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.engine.compiler import compile_ir, rescore
from app.engine.corrigendum import merge, parse_corrigendum
from app.engine.docparse import parse_document, parse_text
from app.engine.guardrails import scan_injection
from app.engine.kb import KnowledgeBase
from app.engine.memory import Memory, twin_to_memory_record
from app.engine.prebid import parse_prebid_document, predict
from app.engine.radar import diff_findings
from app.engine.tender_ir import TenderIR, build_ir, detect_doc_type
from app.models import FindingState, PrebidItem, Tender, TenderDocument
from app.services import ledger_service

logger = logging.getLogger(__name__)
DOC_ORDER = {"tender": 0, "annexure": 1, "corrigendum": 2, "prebid": 3}


async def create_tender(db: AsyncSession, title: str, reference_no: Optional[str] = None, organisation: Optional[str] = None,
                        status: str = "draft", as_of: Optional[date] = None) -> Tender:
    t = Tender(title=title, reference_no=reference_no, organisation=organisation, status=status, as_of_date=as_of)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    await ledger_service.append(db, "buyer", "tender.created", "tender", t.id, {"title": title, "reference_no": reference_no})
    return t


async def add_document(db: AsyncSession, tender: Tender, filename: str, data: bytes, doc_type: Optional[str] = None) -> TenderDocument:
    parsed = parse_document(data, filename)
    text = parsed.text
    dtype = doc_type if doc_type and doc_type != "auto" else detect_doc_type(text, filename)
    if dtype not in DOC_ORDER:
        dtype = "annexure" if dtype in ("datasheet", "certificate", "test_report") else "tender"
    meta = parsed.meta()
    meta["injection_hits"] = scan_injection(text)[:5]
    issued, seq = None, None
    if dtype == "corrigendum":
        pc = parse_corrigendum(text, filename)
        issued, seq = pc.issued_on, pc.number
        meta["operations"] = [o.to_dict() for o in pc.operations]
        meta["unparsed"] = pc.unparsed
    existing = (await db.execute(select(TenderDocument).where(TenderDocument.tender_id == tender.id))).scalars().all()
    if seq is None:
        seq = 1 + len([d for d in existing if d.doc_type == dtype])
    doc = TenderDocument(tender_id=tender.id, doc_type=dtype, filename=filename, sha256=parsed.sha256, sequence_no=seq,
                         issued_on=issued, text=text, parse_meta=meta)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    if dtype == "prebid":
        for q in parse_prebid_document(text):
            db.add(PrebidItem(tender_id=tender.id, qid=f"RQ-{doc.id}-{q['no']}", source="received", clause_key=q["clause_key"],
                              question=q["question"], final_response=q.get("reply"), status="received", data=q))
        await db.commit()
    await ledger_service.append(db, "buyer", "document.added", "tender", tender.id,
                                {"filename": filename, "doc_type": dtype, "sha256": parsed.sha256, "pages": parsed.page_count,
                                 "ocr_pages": parsed.ocr_pages, "parser": parsed.parser})
    return doc


def _combine(irs: List[TenderIR]) -> TenderIR:
    base = irs[0]
    keys = {c.key for c in base.clauses}
    for other in irs[1:]:
        prefix = other.doc_name.rsplit(".", 1)[0][:18]
        for c in other.clauses:
            if c.key in keys:
                c.key = f"{prefix}/{c.key}"
            keys.add(c.key)
            base.clauses.append(c)
        base.sections += other.sections
    return base


async def memory_for(db: AsyncSession, exclude_id: Optional[str] = None) -> Memory:
    rows = (await db.execute(select(Tender).where(Tender.twin.isnot(None)))).scalars().all()
    extra = [twin_to_memory_record(t.twin, t.reference_no or t.id) for t in rows if t.id != exclude_id and t.status in ("closed", "archived", "published")]
    return Memory(extra)


async def compile_tender(db: AsyncSession, tender_id: str, actor: str = "system", reason: str = "manual") -> Dict:
    tender = await db.get(Tender, tender_id)
    if tender is None:
        raise ValueError("tender not found")
    docs = (await db.execute(select(TenderDocument).where(TenderDocument.tender_id == tender_id))).scalars().all()
    docs = sorted(docs, key=lambda d: (DOC_ORDER.get(d.doc_type, 9), d.issued_on or "", d.sequence_no or 0, d.id))
    base_docs = [d for d in docs if d.doc_type in ("tender", "annexure")]
    if not base_docs:
        raise ValueError("tender has no base document")
    irs = [build_ir(parse_text(d.text, d.filename, d.sha256), doc_type="tender") for d in base_docs]
    base_ir = _combine(irs)
    corr = [parse_corrigendum(d.text, d.filename) for d in docs if d.doc_type == "corrigendum"]
    merged = merge(base_ir, corr)
    kb = await KnowledgeBase.from_db(db)
    twin = compile_ir(merged["canonical"], kb, as_of=tender.as_of_date,
                      tender_meta={"id": tender.id, "title": tender.title, "reference_no": tender.reference_no,
                                   "organisation": tender.organisation, "status": tender.status})
    twin["documents"] = [{"id": d.id, "doc_type": d.doc_type, "filename": d.filename, "sha256": d.sha256, "sequence_no": d.sequence_no,
                          "issued_on": d.issued_on, "meta": d.parse_meta} for d in docs]
    twin["corrigenda"] = {"history": merged["history"], "changelog": merged["changelog"], "blame": merged["blame"],
                          "deleted": merged["deleted"], "applied": merged["applied"]}

    # human review state survives recompilation (fingerprints)
    states = {s.fingerprint: s for s in (await db.execute(select(FindingState).where(FindingState.tender_id == tender_id))).scalars().all()}
    for f in twin["findings"]:
        st = states.get(f["fingerprint"])
        f["review_status"] = st.review_status if st else "open"
        if st:
            f["review"] = {"reviewer": st.reviewer, "comment": st.comment, "at": st.updated_at.isoformat() if st.updated_at else None}
    rescore(twin)

    # institutional memory
    mem = await memory_for(db, exclude_id=tender_id)
    all_text = " ".join(c["heading"] + " " + c["text"] for c in twin["clauses"])
    flagged = {f["clause_key"] for f in twin["findings"] if f.get("clause_key") and f["severity"] in ("critical", "major")}
    try:
        from app.services.corpus_service import check_citations
        twin["corpus_check"] = check_citations(twin.get("citations") or [])
    except Exception as e:  # noqa: BLE001 — the corpus is optional
        twin["corpus_check"] = {"available": False, "error": str(e)[:200]}
    twin["memory"] = {
        "similar_tenders": mem.similar_tenders(twin["tender"]["title"] + " " + all_text),
        "clause_precedents": {c["key"]: mem.clause_precedents(c["text"], k=2) for c in twin["clauses"] if c["key"] in flagged and c.get("text")},
        "recurring_patterns": mem.recurring_patterns()[:8],
    }
    twin["memory"]["clause_precedents"] = {k: v for k, v in twin["memory"]["clause_precedents"].items() if v}

    # pre-bid predictions merged with stored decisions + received queries
    preds = predict(twin, mem)
    stored = {p.qid: p for p in (await db.execute(select(PrebidItem).where(PrebidItem.tender_id == tender_id))).scalars().all()}
    for p in preds:
        if p["id"] in stored:
            s = stored[p["id"]]
            p["status"], p["final_response"] = s.status, s.final_response
        else:
            db.add(PrebidItem(tender_id=tender_id, qid=p["id"], source="predicted", clause_key=p["clause_key"], question=p["question"],
                              likelihood=p["likelihood"], draft_response=p["draft_response"], status="predicted",
                              finding_fingerprint=p["finding_fingerprint"], data={"rule_id": p["rule_id"]}))
    received = [{"id": s.qid, "clause_key": s.clause_key, "question": s.question, "final_response": s.final_response, "status": s.status,
                 "source": "received"} for s in stored.values() if s.source == "received"]
    twin["prebid"] = preds
    twin["prebid_received"] = received

    # regression / delta vs previous compile
    if tender.twin and tender.twin.get("findings") is not None:
        d = diff_findings(tender.twin["findings"], twin["findings"])
        twin["delta"] = {"introduced": [{"rule_id": f["rule_id"], "clause_key": f.get("clause_key"), "severity": f["severity"], "message": f["message"]} for f in d["introduced"]],
                         "resolved": [{"rule_id": f["rule_id"], "clause_key": f.get("clause_key"), "severity": f["severity"], "message": f["message"]} for f in d["resolved"]],
                         "previous_score": (tender.twin.get("readiness") or {}).get("score"), "reason": reason}
    tender.twin = twin
    flag_modified(tender, "twin")
    tender.compiled_at = datetime.utcnow()
    tender.readiness_score = twin["readiness"]["score"]
    tender.gate = twin["readiness"]["gate"]
    await db.commit()
    await ledger_service.append(db, actor, "tender.compiled", "tender", tender_id, {
        "reason": reason, "documents": [{"f": d.filename, "sha256": d.sha256} for d in docs],
        "kb_snapshot": twin["provenance"]["kb_snapshot"], "engine": twin["provenance"]["engine"], "solver": twin["provenance"]["solver"],
        "readiness": twin["readiness"]["score"], "gate": twin["readiness"]["gate"], "findings": len(twin["findings"]),
        "content_hash": twin["provenance"]["content_hash"]})
    return twin


async def set_finding_review(db: AsyncSession, tender_id: str, fingerprint: str, status: str, reviewer: str, comment: Optional[str]) -> Dict:
    st = (await db.execute(select(FindingState).where(FindingState.tender_id == tender_id, FindingState.fingerprint == fingerprint))).scalars().first()
    tender = await db.get(Tender, tender_id)
    rule_id = None
    if tender and tender.twin:
        f = next((f for f in tender.twin["findings"] if f["fingerprint"] == fingerprint), None)
        rule_id = f["rule_id"] if f else None
    if st is None:
        st = FindingState(tender_id=tender_id, fingerprint=fingerprint, rule_id=rule_id)
        db.add(st)
    st.review_status, st.reviewer, st.comment = status, reviewer, comment
    if tender and tender.twin:
        twin = dict(tender.twin)
        for f in twin["findings"]:
            if f["fingerprint"] == fingerprint:
                f["review_status"] = status
                f["review"] = {"reviewer": reviewer, "comment": comment, "at": datetime.utcnow().isoformat()}
        rescore(twin)
        tender.twin = twin
        flag_modified(tender, "twin")
        tender.readiness_score = twin["readiness"]["score"]
        tender.gate = twin["readiness"]["gate"]
    await db.commit()
    await ledger_service.append(db, reviewer or "reviewer", "finding.reviewed", "finding", fingerprint,
                                {"tender_id": tender_id, "rule_id": rule_id, "decision": status, "comment": comment})
    return {"fingerprint": fingerprint, "review_status": status, "readiness": tender.twin["readiness"] if tender and tender.twin else None}
