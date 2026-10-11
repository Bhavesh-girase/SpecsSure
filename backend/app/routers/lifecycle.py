"""Tender lifecycle: contractor queries, bid/no-bid advice, closing, sealed financial opening, evaluation, award, dashboards."""
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine import exporters
from app.services import lifecycle_service as ls

router = APIRouter()


@router.post("/tenders/{tender_id}/queries", summary="Contractor raises a clarification query (auto-located to a clause, de-duplicated, draft reply)")
async def raise_query(tender_id: str, bidder: str = Body(...), question: str = Body(...), clause_key: Optional[str] = Body(None),
                      db: AsyncSession = Depends(get_db)):
    if len(question.strip()) < 8:
        raise HTTPException(400, "Question is too short")
    try:
        return await ls.raise_query(db, tender_id, bidder, question, clause_key)
    except ValueError:
        raise HTTPException(404, "Tender not found")


@router.get("/tenders/{tender_id}/queries", summary="Clarification queries (public=true → only published replies, bidder identity hidden)")
async def list_queries(tender_id: str, public: bool = False, db: AsyncSession = Depends(get_db)):
    return await ls.list_queries(db, tender_id, public_only=public)


@router.post("/tenders/{tender_id}/queries/{qid}/answer", summary="Officer answers a query (approved / published / rejected)")
async def answer_query(tender_id: str, qid: str, response: str = Body(...), status: str = Body("published"), officer: str = Body("tender-officer"),
                       db: AsyncSession = Depends(get_db)):
    if status not in ("approved", "published", "rejected"):
        raise HTTPException(400, "status must be approved | published | rejected")
    try:
        return await ls.answer_query(db, tender_id, qid, response, status, officer)
    except ValueError:
        raise HTTPException(404, "Query not found")


@router.post("/tenders/{tender_id}/bid-form/advice", summary="Bid / No-Bid advisor with a back-scheduled preparation plan")
async def advice(tender_id: str, payload: Dict = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        return await ls.advice(db, tender_id, payload.get("answers") or {}, payload.get("scope"))
    except ValueError:
        raise HTTPException(404, "Tender not found")


@router.get("/tenders/{tender_id}/evaluation", summary="Evaluation (technical → sealed financial → L1 → Make in India → MSE → award proposal)")
async def evaluation(tender_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await ls.evaluation(db, tender_id)
    except ValueError:
        raise HTTPException(404, "Tender not found")


@router.post("/tenders/{tender_id}/close-bidding", summary="Close bidding (no further submissions)")
async def close(tender_id: str, officer: str = Body("tender-officer", embed=True), db: AsyncSession = Depends(get_db)):
    return await ls.close_bidding(db, tender_id, officer)


@router.post("/tenders/{tender_id}/open-financial", summary="Open sealed financial bids — every price is verified against its ledgered commitment")
async def open_financial(tender_id: str, officer: str = Body("tender-officer", embed=True), db: AsyncSession = Depends(get_db)):
    try:
        return await ls.open_financial(db, tender_id, officer)
    except ValueError:
        raise HTTPException(404, "Tender not found")


@router.post("/tenders/{tender_id}/award", summary="Record the committee's award decision (from the evaluation proposal)")
async def award(tender_id: str, officer: str = Body("tender-officer"), remarks: Optional[str] = Body(None), db: AsyncSession = Depends(get_db)):
    try:
        return await ls.award(db, tender_id, officer, remarks)
    except ValueError:
        raise HTTPException(404, "Tender not found")
    except PermissionError as e:
        raise HTTPException(409, str(e))


@router.get("/tenders/{tender_id}/evaluation/report.pdf", summary="Evaluation & award report (PDF)")
async def report(tender_id: str, db: AsyncSession = Depends(get_db)):
    try:
        ev = await ls.evaluation(db, tender_id)
    except ValueError:
        raise HTTPException(404, "Tender not found")
    pdf = exporters.evaluation_pdf(ev["tender"]["title"], ev["tender"]["reference_no"] or ev["tender"]["id"], ev, ev.get("award"))
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="evaluation_{tender_id}.pdf"'})


@router.get("/dashboard/officer", summary="Procurement officer workspace: tenders by stage and pending actions")
async def officer(db: AsyncSession = Depends(get_db)):
    return await ls.officer_dashboard(db)


@router.get("/dashboard/contractor", summary="Contractor workspace: open tenders, my bids and results")
async def contractor(bidder: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await ls.contractor_dashboard(db, bidder)


@router.get("/stats", summary="Portal statistics")
async def stats(db: AsyncSession = Depends(get_db)):
    return await ls.stats(db)
