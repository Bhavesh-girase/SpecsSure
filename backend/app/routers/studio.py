"""Tender Studio (buyer): one sentence → clarifying questions → verified, fully-traceable tender draft."""
from datetime import date
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine import intent as intent_engine
from app.engine.kg import items
from app.engine.synthesizer import to_docx
from app.models import Tender
from app.services import studio_service

router = APIRouter()

EXAMPLES = [
    {"lang": "en", "text": "need a tender of 500 light bulbs and 100 meteres"},
    {"lang": "hinglish", "text": "500 LED bulb 9 watt aur 100 meter 2.5 sq mm taar chahiye, 30 din mein, budget 2 lakh"},
    {"lang": "hi", "text": "पाँच सौ बल्ब और सौ मीटर तार"},
    {"lang": "en", "text": "20 ceiling fans 1200mm, 50 MCB 16A C curve and 2 coils of 4 sq mm FRLS copper wire for PHC Rampur within 45 days"},
    {"lang": "en", "text": "120 solar panels 540Wp for school rooftop, budget 20 lakh"},
    {"lang": "en", "text": "Need 400 bags of 53 grade cement and 5 tonnes Fe 500D TMT 8mm 12mm 16mm"},
]


@router.get("/studio/catalogue", summary="Items the Tender Studio can draft (KG item layer) + example requests")
async def catalogue():
    return {"items": [{k: it[k] for k in ("id", "label", "domain", "default_unit", "unit_kind", "aliases", "slots")} for it in items()],
            "examples": EXAMPLES}


@router.post("/studio/parse", summary="Parse a one-line request (English / Hindi / Hinglish) into line items + only the questions that matter")
async def parse(payload: Dict = Body(..., examples=[{"text": "need a tender of 500 light bulbs and 100 meteres"}])):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    res = intent_engine.parse(text)
    sug = await intent_engine.llm_suggest(text)
    if sug:
        res["llm_suggestion"] = sug
    return res


@router.post("/studio/generate", summary="Generate a verified tender draft from a parsed intent (+answers)")
async def generate(payload: Dict = Body(...), db: AsyncSession = Depends(get_db)):
    intent = payload.get("intent") or intent_engine.parse(payload.get("text") or "")
    if payload.get("answers"):
        intent = intent_engine.apply_answers(intent, payload["answers"])
    as_of = date.fromisoformat(payload["as_of"]) if payload.get("as_of") else None
    try:
        gen = await studio_service.generate(db, intent, as_of, payload.get("meta") or {}, payload.get("overrides"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    gen["intent"] = intent
    return gen


@router.post("/studio/save", summary="Generate and save as a draft tender (opens in the Tender cockpit)")
async def save(payload: Dict = Body(...), db: AsyncSession = Depends(get_db)):
    intent = payload.get("intent") or intent_engine.parse(payload.get("text") or "")
    if payload.get("answers"):
        intent = intent_engine.apply_answers(intent, payload["answers"])
    as_of = date.fromisoformat(payload["as_of"]) if payload.get("as_of") else None
    try:
        gen = await studio_service.generate(db, intent, as_of, payload.get("meta") or {}, payload.get("overrides"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    t = await studio_service.save_generated(db, gen, intent, actor=(payload.get("meta") or {}).get("officer") or "buyer")
    if payload.get("publish") and t.gate != "BLOCKED":
        t.status = "published"
        await db.commit()
    return {"tender_id": t.id, "status": t.status, "gate": t.gate, "readiness": t.readiness_score}


@router.post("/studio/docx", summary="Download a generated draft as Word (with clause-traceability annex)")
async def docx_from_payload(payload: Dict = Body(...), db: AsyncSession = Depends(get_db)):
    gen = payload.get("generation")
    if not gen:
        intent = payload.get("intent") or intent_engine.parse(payload.get("text") or "")
        if payload.get("answers"):
            intent = intent_engine.apply_answers(intent, payload["answers"])
        gen = await studio_service.generate(db, intent, None, payload.get("meta") or {}, payload.get("overrides"))
    return Response(to_docx(gen), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": 'attachment; filename="tender_draft.docx"'})


@router.get("/tenders/{tender_id}/generated.docx", summary="Word export of a Studio-generated tender")
async def docx_for_tender(tender_id: str, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tender, tender_id)
    if t is None or not t.generation:
        raise HTTPException(404, "Not a Studio-generated tender")
    g = dict(t.generation)
    g.setdefault("text", "")
    return Response(to_docx(g), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="tender_{tender_id}.docx"'})


@router.get("/tenders/{tender_id}/generation", summary="Studio provenance for a generated tender (clause basis, KG paths, verification passes)")
async def generation(tender_id: str, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tender, tender_id)
    if t is None or not t.generation:
        raise HTTPException(404, "Not a Studio-generated tender")
    return t.generation
