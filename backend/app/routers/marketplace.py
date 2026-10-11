"""Contractor marketplace: open tenders, auto-derived bid form, live Tender Match Index, submission, comparative statement, OCR."""
import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine import bidform
from app.engine.ocr import available_engines, ocr_image
from app.models import Bid, Tender
from app.services import studio_service

router = APIRouter()


@router.get("/market/tenders", summary="Published tenders open for bidding")
async def open_tenders(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Tender).where(Tender.status == "published").order_by(Tender.created_at.desc()))).scalars().all()
    counts = dict((await db.execute(select(Bid.tender_id, func.count(Bid.id)).group_by(Bid.tender_id))).all())
    out = []
    for t in rows:
        tw = t.twin or {}
        dates = (tw.get("tender") or {}).get("dates", {})
        items = []
        if t.generation:
            items = [{"label": l["item_label"], "quantity": l["quantity"], "unit": l["unit"]} for l in t.generation.get("lines", [])]
        out.append({"id": t.id, "title": t.title, "reference_no": t.reference_no, "organisation": t.organisation, "bid_due": dates.get("bid_due"),
                    "publication": dates.get("publication"), "domains": (tw.get("tender") or {}).get("domains", []), "items": items,
                    "readiness": t.readiness_score, "gate": t.gate, "bids": counts.get(t.id, 0), "generated": bool(t.generation),
                    "requirements": len(tw.get("requirements", []))})
    return out


@router.get("/tenders/{tender_id}/bid-form", summary="Bid response form derived from the canonical tender (after corrigenda)")
async def get_form(tender_id: str, db: AsyncSession = Depends(get_db)):
    try:
        _, form = await studio_service.form_for(db, tender_id)
    except ValueError:
        raise HTTPException(404, "Tender not found")
    return form


@router.post("/tenders/{tender_id}/bid-form/score", summary="Live Tender Match Index for the current answers")
async def score_form(tender_id: str, payload: Dict = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        _, form = await studio_service.form_for(db, tender_id)
    except ValueError:
        raise HTTPException(404, "Tender not found")
    return bidform.score(form, payload.get("answers") or {}, scope=payload.get("scope"))


@router.post("/tenders/{tender_id}/bid-form/autofill", summary="Read datasheets / licences / test reports (incl. scans via OCR) and pre-fill the form")
async def autofill(tender_id: str, files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    try:
        _, form = await studio_service.form_for(db, tender_id)
    except ValueError:
        raise HTTPException(404, "Tender not found")
    payload = [(f.filename or f"doc_{i}", await f.read()) for i, f in enumerate(files)]
    docs, meta, security = studio_service.evidence_from_files(payload)
    answers = bidform.autofill(form, docs)
    scope = bidform.infer_scope(form, docs)
    return {"answers": answers, "scope": scope, "files": meta, "security_flags": security,
            "score": bidform.score(form, answers, scope=scope)}


@router.post("/tenders/{tender_id}/bid-form/submit", summary="Submit a bid: typed answers + supporting documents")
async def submit(tender_id: str, bidder: str = Form(...), product_name: Optional[str] = Form(None), answers: str = Form("{}"),
                 scope: Optional[str] = Form(None), financial: Optional[str] = Form(None, description='Sealed price bid JSON {"lines":{"1":{"unit_price":72}}}'),
                 declarations: Optional[str] = Form(None, description='JSON {"mse":true,"mii_class":"I","local_content":62}'),
                 files: List[UploadFile] = File(default=[]), db: AsyncSession = Depends(get_db)):
    t = await db.get(Tender, tender_id)
    if t is None:
        raise HTTPException(404, "Tender not found")
    if (t.award or {}).get("bids_closed") or t.status not in ("published", "draft"):
        raise HTTPException(409, "Bidding is closed for this tender")
    try:
        ans = json.loads(answers or "{}")
        fin = json.loads(financial) if financial else None
        decl = json.loads(declarations) if declarations else None
    except json.JSONDecodeError:
        raise HTTPException(400, "answers / financial / declarations must be JSON")
    payload = [(f.filename or f"doc_{i}", await f.read()) for i, f in enumerate(files or [])]
    bid = await studio_service.submit_bid(db, tender_id, bidder, product_name, ans, [s for s in (scope or "").split(",") if s] or None, payload,
                                          financial=fin, declarations=decl)
    return {"bid_id": bid.id, "match_index": bid.match_index, "tier": bid.form["score"]["tier"], "verdict": bid.verdict,
            "financial_commitment": bid.form.get("commitment"),
            "receipt": "Your price bid is sealed: only its SHA-256 commitment is recorded in the audit ledger until the financial opening."}


@router.get("/tenders/{tender_id}/comparative", summary="Comparative statement of technical bids (for the evaluation committee)")
async def comparative(tender_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await studio_service.comparative(db, tender_id)
    except ValueError:
        raise HTTPException(404, "Tender not found")


@router.get("/ocr/engines", summary="Available OCR engines")
async def engines():
    return {"engines": available_engines(), "primary": "RapidOCR 3 · PaddleOCR PP-OCRv6 (ONNX, CPU) + PP-OCRv5 Devanagari",
            "fallback": "Tesseract (if installed)"}


@router.post("/ocr", summary="OCR an image (scan / photo) with confidence, boxes and domain-aware repairs")
async def ocr(file: UploadFile = File(...)):
    data = await file.read()
    name = (file.filename or "").lower()
    if name.endswith(".pdf"):
        from app.engine.docparse import parse_document
        p = parse_document(data, file.filename)
        return {"text": p.text, "meta": p.meta(), "warnings": p.warnings}
    r = ocr_image(data)
    d = r.to_dict()
    d["lines"] = [{"text": l.text, "conf": round(l.conf, 3), "box": l.box, "script": l.script} for l in r.lines]
    return d
