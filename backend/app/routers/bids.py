"""Contractor / bidder workspace: Bid Mirror, compliance matrix, evidence package, compliance passport."""
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine import exporters
from app.engine import passport as vc
from app.models import Bid, Passport, Tender
from app.services import bid_service, tender_service

router = APIRouter()


def _bid_summary(b: Bid) -> dict:
    return {"id": b.id, "tender_id": b.tender_id, "bidder": b.bidder, "product_name": b.product_name,
            "compliance_score": b.compliance_score, "verdict": b.verdict, "match_index": b.match_index,
            "tier": ((b.form or {}).get("score") or {}).get("tier"), "created_at": b.created_at.isoformat() if b.created_at else None}


@router.get("/bids", summary="List bids")
async def list_bids(tender_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Bid).order_by(Bid.created_at.desc())
    if tender_id:
        stmt = stmt.where(Bid.tender_id == tender_id)
    return [_bid_summary(b) for b in (await db.execute(stmt)).scalars().all()]


@router.post("/bids", summary="Bid Mirror: upload datasheets / certificates / test reports against a tender")
async def create_bid(
    bidder: str = Form(...),
    product_name: Optional[str] = Form(None),
    tender_id: Optional[str] = Form(None, description="Existing tender id — or upload tender_file"),
    tender_file: Optional[UploadFile] = File(None, description="Contractor's own copy of the tender"),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not tender_id:
        if tender_file is None:
            raise HTTPException(400, "Provide tender_id or tender_file.")
        t = await tender_service.create_tender(db, f"Bidder copy — {tender_file.filename}", status="bidder_copy")
        await tender_service.add_document(db, t, tender_file.filename or "tender.txt", await tender_file.read(), "tender")
        await tender_service.compile_tender(db, t.id, actor=bidder, reason="bidder copy")
        tender_id = t.id
    elif await db.get(Tender, tender_id) is None:
        raise HTTPException(404, "Tender not found")
    payload = [(f.filename or f"evidence_{i}.txt", await f.read()) for i, f in enumerate(files)]
    bid = await bid_service.create_bid(db, tender_id, bidder, product_name, payload)
    return {**_bid_summary(bid), "result": bid.result}


@router.get("/bids/{bid_id}", summary="Bid Mirror result (compliance matrix)")
async def get_bid(bid_id: str, db: AsyncSession = Depends(get_db)):
    b = await db.get(Bid, bid_id)
    if b is None:
        raise HTTPException(404, "Bid not found")
    passports = (await db.execute(select(Passport).where(Passport.bid_id == bid_id))).scalars().all()
    return {**_bid_summary(b), "result": b.result, "evidence": b.evidence, "passports": [p.id for p in passports],
            "form": b.form, "match_index": b.match_index}


@router.get("/bids/{bid_id}/export/matrix.xlsx", summary="Compliance matrix (Excel)")
async def export_matrix(bid_id: str, db: AsyncSession = Depends(get_db)):
    b = await db.get(Bid, bid_id)
    if b is None:
        raise HTTPException(404, "Bid not found")
    return Response(exporters.compliance_matrix_xlsx(b.result), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="compliance_matrix_{bid_id}.xlsx"'})


@router.get("/bids/{bid_id}/export/evidence-package.zip", summary="Tamper-evident evidence package (matrix + files + SHA-256 manifest + passport)")
async def export_package(bid_id: str, db: AsyncSession = Depends(get_db)):
    b = await db.get(Bid, bid_id)
    if b is None:
        raise HTTPException(404, "Bid not found")
    files = [{"name": d.filename, "bytes": d.content or (d.text or "").encode()} for d in await bid_service.bid_files(db, bid_id)]
    p = (await db.execute(select(Passport).where(Passport.bid_id == bid_id).order_by(Passport.created_at.desc()))).scalars().first()
    return Response(exporters.evidence_package_zip(b.result, files, p.credential if p else None), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="evidence_package_{bid_id}.zip"'})


@router.post("/bids/{bid_id}/passport", summary="Issue a Product Compliance Passport (W3C Verifiable Credential)")
async def issue_passport(bid_id: str, db: AsyncSession = Depends(get_db)):
    try:
        p = await bid_service.issue_passport(db, bid_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"id": p.id, "credential": p.credential, "verification": vc.verify(p.credential)}


@router.get("/passports", summary="List passports")
async def list_passports(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Passport).order_by(Passport.created_at.desc()))).scalars().all()
    return [{"id": p.id, "product_name": p.product_name, "bid_id": p.bid_id, "created_at": p.created_at.isoformat(),
             "issuer": p.credential["issuer"]["id"], "revoked": p.revoked} for p in rows]


@router.get("/passports/{pid}", summary="Get a passport with live verification + QR")
async def get_passport(pid: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Passport, pid)
    if p is None:
        raise HTTPException(404, "Passport not found")
    from app.config import settings
    url = f"{settings.FRONTEND_URL}/passport/{pid}"
    return {"id": p.id, "credential": p.credential, "verification": {**vc.verify(p.credential), "revoked": p.revoked},
            "qr": vc.qr_data_uri(url), "verify_url": url}


@router.post("/passports/verify", summary="Verify any passport credential (offline-verifiable Ed25519 proof)")
async def verify_passport(credential: dict = Body(...)):
    return vc.verify(credential)


@router.post("/bids/{bid_id}/rerun", summary="Re-mirror the stored evidence against the tender's latest (corrigenda-merged) twin")
async def rerun_bid(bid_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm.attributes import flag_modified
    from app.engine.bidmirror import mirror
    from app.services import ledger_service
    b = await db.get(Bid, bid_id)
    if b is None:
        raise HTTPException(404, "Bid not found")
    t = await db.get(Tender, b.tender_id)
    twin = t.twin or await tender_service.compile_tender(db, t.id, reason="bid rerun")
    res = mirror(twin, b.evidence or [], bidder=b.bidder)
    res["product_name"] = b.product_name
    res["security_flags"] = (b.result or {}).get("security_flags", [])
    b.result, b.compliance_score, b.verdict = res, res["compliance_score"], res["verdict"]
    flag_modified(b, "result")
    await db.commit()
    await ledger_service.append(db, b.bidder, "bid.re-mirrored", "bid", bid_id, {"verdict": res["verdict"], "score": res["compliance_score"],
                                                                                "tender_kb": twin["provenance"]["kb_snapshot"]})
    return {**_bid_summary(b), "result": res}
