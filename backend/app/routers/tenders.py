"""Buyer workspace: Tender Digital Twin, linter, corrigenda, pre-bid, exports."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import get_db
from app.engine import exporters
from app.engine.corrigendum import canonical_text, fixes_to_corrigendum
from app.engine.sarif import to_sarif
from app.models import PrebidItem, Tender, TenderDocument
from app.services import ledger_service, tender_service

router = APIRouter()


def _summary(t: Tender) -> dict:
    tw = t.twin or {}
    rd = tw.get("readiness") or {}
    return {"id": t.id, "title": t.title, "reference_no": t.reference_no, "organisation": t.organisation, "status": t.status,
            "readiness_score": t.readiness_score, "gate": t.gate, "counts": rd.get("counts"), "domains": (tw.get("tender") or {}).get("domains"),
            "compiled_at": t.compiled_at.isoformat() if t.compiled_at else None, "created_at": t.created_at.isoformat() if t.created_at else None,
            "documents": len(tw.get("documents") or []), "generated": bool(getattr(t, "generation", None))}


async def _get(db, tender_id) -> Tender:
    t = await db.get(Tender, tender_id)
    if t is None:
        raise HTTPException(404, "Tender not found")
    return t


async def _twin(db, tender_id) -> dict:
    t = await _get(db, tender_id)
    if not t.twin:
        return await tender_service.compile_tender(db, tender_id, reason="lazy")
    return t.twin


@router.get("/tenders", summary="List tenders (buyer workspace)")
async def list_tenders(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Tender).order_by(Tender.created_at.desc())
    if status:
        stmt = stmt.where(Tender.status == status)
    return [_summary(t) for t in (await db.execute(stmt)).scalars().all()]


@router.post("/tenders", summary="Create a tender from one or more documents and compile its Digital Twin")
async def create_tender(
    title: str = Form(...),
    reference_no: Optional[str] = Form(None),
    organisation: Optional[str] = Form(None),
    status: str = Form("draft"),
    as_of_date: Optional[str] = Form(None, description="YYYY-MM-DD; default = publication date found in the tender"),
    text: Optional[str] = Form(None, description="Paste tender text instead of uploading"),
    files: List[UploadFile] = File(default=[]),
    doc_types: Optional[str] = Form(None, description="Comma-separated doc types matching files order (tender/annexure/corrigendum/prebid/auto)"),
    db: AsyncSession = Depends(get_db),
):
    if not files and not (text and text.strip()):
        raise HTTPException(400, "Provide at least one document or pasted text.")
    t = await tender_service.create_tender(db, title, reference_no, organisation, status,
                                           date.fromisoformat(as_of_date) if as_of_date else None)
    types = [x.strip() for x in (doc_types or "").split(",")] if doc_types else []
    if text and text.strip():
        await tender_service.add_document(db, t, "pasted_tender.txt", text.encode("utf-8"), "tender")
    for i, f in enumerate(files):
        data = await f.read()
        await tender_service.add_document(db, t, f.filename or f"document_{i}.txt", data, types[i] if i < len(types) else "auto")
    twin = await tender_service.compile_tender(db, t.id, actor="buyer", reason="created")
    return {"id": t.id, "readiness": twin["readiness"], "findings": len(twin["findings"])}


@router.get("/tenders/{tender_id}", summary="Tender Digital Twin (full)")
async def get_tender(tender_id: str, db: AsyncSession = Depends(get_db)):
    t = await _get(db, tender_id)
    tw = await _twin(db, tender_id)
    return {"summary": _summary(t), "twin": tw}


@router.post("/tenders/{tender_id}/documents", summary="Add a corrigendum / annexure / pre-bid document and re-compile")
async def add_document(tender_id: str, file: UploadFile = File(...), doc_type: str = Form("auto"), db: AsyncSession = Depends(get_db)):
    t = await _get(db, tender_id)
    doc = await tender_service.add_document(db, t, file.filename or "document.txt", await file.read(), doc_type)
    twin = await tender_service.compile_tender(db, tender_id, actor="buyer", reason=f"{doc.doc_type} added: {doc.filename}")
    return {"document_id": doc.id, "doc_type": doc.doc_type, "readiness": twin["readiness"], "delta": twin.get("delta")}


@router.post("/tenders/{tender_id}/compile", summary="Re-compile (re-validate) the twin")
async def recompile(tender_id: str, db: AsyncSession = Depends(get_db)):
    await _get(db, tender_id)
    twin = await tender_service.compile_tender(db, tender_id, actor="buyer", reason="manual revalidation")
    return {"readiness": twin["readiness"], "delta": twin.get("delta"), "provenance": twin["provenance"]}


@router.patch("/tenders/{tender_id}", summary="Update tender status / as-of date")
async def update_tender(tender_id: str, status: Optional[str] = Body(None), as_of_date: Optional[str] = Body(None),
                        db: AsyncSession = Depends(get_db)):
    t = await _get(db, tender_id)
    if status:
        if status == "published" and t.gate == "BLOCKED":
            raise HTTPException(409, "Pre-publication validation failed: open critical findings. Resolve or record a review decision first.")
        t.status = status
    if as_of_date is not None:
        t.as_of_date = date.fromisoformat(as_of_date) if as_of_date else None
    await db.commit()
    await ledger_service.append(db, "buyer", "tender.updated", "tender", tender_id, {"status": status, "as_of_date": as_of_date})
    if as_of_date is not None:
        await tender_service.compile_tender(db, tender_id, reason="as-of date changed")
    return _summary(t)


@router.patch("/tenders/{tender_id}/findings/{fingerprint}", summary="Human review of a finding (accept / dismiss / fixed)")
async def review_finding(tender_id: str, fingerprint: str, review_status: str = Body(...), reviewer: str = Body("Reviewer"),
                         comment: Optional[str] = Body(None), db: AsyncSession = Depends(get_db)):
    if review_status not in ("open", "accepted", "dismissed", "fixed"):
        raise HTTPException(400, "review_status must be open|accepted|dismissed|fixed")
    if review_status == "dismissed" and not (comment and comment.strip()):
        raise HTTPException(400, "Dismissing a finding requires a justification comment (audit requirement).")
    return await tender_service.set_finding_review(db, tender_id, fingerprint, review_status, reviewer, comment)


@router.get("/tenders/{tender_id}/sarif", summary="Linter results as SARIF 2.1.0")
async def sarif(tender_id: str, db: AsyncSession = Depends(get_db)):
    tw = await _twin(db, tender_id)
    return JSONResponse(to_sarif(tw), headers={"Content-Disposition": f'attachment; filename="tender_{tender_id}.sarif"'})


@router.get("/tenders/{tender_id}/canonical", summary="Canonical (corrigenda-merged) tender with clause blame")
async def canonical(tender_id: str, format: str = Query("json"), db: AsyncSession = Depends(get_db)):
    tw = await _twin(db, tender_id)
    corr = tw.get("corrigenda") or {}
    if format == "text":
        from app.engine.tender_ir import TenderIR, Clause
        ir = TenderIR(tw["tender"]["title"], "tender", tw["tender"]["title"],
                      [Clause(**{k: c[k] for k in ("key", "heading", "text", "page_start", "page_end", "doc_name", "section", "section_type", "parent", "annexure", "tables")}) for c in tw["clauses"]], [])
        return Response(canonical_text(ir, corr.get("blame")), media_type="text/plain")
    return {"clauses": tw["clauses"], "blame": corr.get("blame"), "changelog": corr.get("changelog"), "deleted": corr.get("deleted")}


@router.get("/tenders/{tender_id}/clauses/{clause_key}/history", summary="Version history of one clause")
async def clause_history(tender_id: str, clause_key: str, db: AsyncSession = Depends(get_db)):
    tw = await _twin(db, tender_id)
    h = (tw.get("corrigenda") or {}).get("history", {}).get(clause_key)
    if h is None:
        raise HTTPException(404, "Clause not found")
    return {"clause_key": clause_key, "versions": h, "latest": h[-1]}


@router.post("/tenders/{tender_id}/autofix", summary="Render selected autofixes as a draft corrigendum")
async def autofix(tender_id: str, fingerprints: List[str] = Body(...), issued_on: Optional[str] = Body(None), apply: bool = Body(False),
                  db: AsyncSession = Depends(get_db)):
    t = await _get(db, tender_id)
    tw = await _twin(db, tender_id)
    docs = (await db.execute(select(TenderDocument).where(TenderDocument.tender_id == tender_id, TenderDocument.doc_type == "corrigendum"))).scalars().all()
    number = 1 + max([d.sequence_no or 0 for d in docs] or [0])
    draft = fixes_to_corrigendum(tw, fingerprints, number, issued_on or date.today().isoformat(), t.reference_no or t.id)
    result = {"draft": draft}
    if apply and draft["items"]:
        doc = await tender_service.add_document(db, t, f"corrigendum_{number}_draft.txt", draft["text"].encode(), "corrigendum")
        twin = await tender_service.compile_tender(db, tender_id, actor="buyer", reason=f"autofix corrigendum {number}")
        result.update({"applied": True, "document_id": doc.id, "readiness": twin["readiness"], "delta": twin.get("delta")})
    return result


@router.post("/tenders/{tender_id}/prebid/{qid}", summary="Approve / edit / reject a pre-bid clarification")
async def prebid_decision(tender_id: str, qid: str, status: str = Body(...), final_response: Optional[str] = Body(None),
                          reviewer: str = Body("Tender committee"), db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(PrebidItem).where(PrebidItem.tender_id == tender_id, PrebidItem.qid == qid))).scalars().first()
    if item is None:
        raise HTTPException(404, "Pre-bid item not found")
    item.status = status
    if final_response is not None:
        item.final_response = final_response
    t = await _get(db, tender_id)
    if t.twin:
        tw = t.twin
        for p in tw.get("prebid", []) + tw.get("prebid_received", []):
            if p["id"] == qid:
                p["status"], p["final_response"] = status, item.final_response
        t.twin = tw
        flag_modified(t, "twin")
    await db.commit()
    await ledger_service.append(db, reviewer, "prebid.decision", "prebid", qid, {"tender_id": tender_id, "status": status, "response": item.final_response})
    return {"qid": qid, "status": status, "final_response": item.final_response}


@router.post("/tenders/{tender_id}/prebid-propagate", summary="Propagate approved clarifications that change clauses into a draft corrigendum")
async def prebid_propagate(tender_id: str, apply: bool = Body(False, embed=True), db: AsyncSession = Depends(get_db)):
    tw = await _twin(db, tender_id)
    fps = [p["finding_fingerprint"] for p in tw.get("prebid", []) if p.get("status") in ("approved", "published") and p.get("finding_fingerprint")]
    if not fps:
        raise HTTPException(400, "No approved clarifications with clause changes.")
    return await autofix(tender_id, fps, None, apply, db)


@router.get("/tenders/{tender_id}/export/findings.xlsx", summary="Findings register + requirements + checklist (Excel)")
async def export_findings(tender_id: str, db: AsyncSession = Depends(get_db)):
    tw = await _twin(db, tender_id)
    return Response(exporters.findings_xlsx(tw), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="tender_{tender_id}_findings.xlsx"'})


@router.get("/tenders/{tender_id}/export/report.pdf", summary="Readiness report (PDF)")
async def export_pdf(tender_id: str, db: AsyncSession = Depends(get_db)):
    tw = await _twin(db, tender_id)
    return Response(exporters.readiness_pdf(tw), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="tender_{tender_id}_readiness.pdf"'})


@router.get("/tenders/{tender_id}/twin.json", summary="Download the complete Digital Twin JSON")
async def export_twin(tender_id: str, db: AsyncSession = Depends(get_db)):
    tw = await _twin(db, tender_id)
    return JSONResponse(tw, headers={"Content-Disposition": f'attachment; filename="tender_{tender_id}_twin.json"'})


@router.post("/tenders/{tender_id}/findings/{fingerprint}/explain", summary="Plain-language / Hindi explanation of a finding (LLM, evidence-fenced, labelled AI)")
async def explain_finding(tender_id: str, fingerprint: str, lang: str = Body("en", embed=True), db: AsyncSession = Depends(get_db)):
    from app.engine.guardrails import SYSTEM_RULES, fence
    from app.services.llm_service import llm_service
    tw = await _twin(db, tender_id)
    f = next((x for x in tw["findings"] if x["fingerprint"] == fingerprint), None)
    if f is None:
        raise HTTPException(404, "Finding not found")
    facts = {k: f.get(k) for k in ("rule_name", "message", "suggestion", "basis", "quote", "clause_key")}
    language = {"hi": "Hindi", "mr": "Marathi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali"}.get(lang, "simple English")
    prompt = (f"Explain this tender-review finding to a procurement officer in {language}, in at most 4 sentences. "
              f"Use ONLY the facts provided; keep IS numbers, clause numbers and values unchanged.\n{fence(str(facts), 'document')}")
    text = await llm_service.generate_text(prompt, system_instruction=SYSTEM_RULES)
    if not text:
        text = f"{f['message']} Suggested action: {f.get('suggestion') or '—'}"
        return {"text": text, "generated_by": "deterministic-template", "note": "LLM not configured (set GEMINI_API_KEY) — showing the rule engine's own wording."}
    return {"text": text.strip(), "generated_by": "llm", "label": "AI-generated explanation of a deterministic finding — verify against the evidence."}
