"""Audit ledger & governance."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import LedgerEntry
from app.services import ledger_service

router = APIRouter()


@router.get("/ledger", summary="Tamper-evident audit ledger (latest first)")
async def ledger(limit: int = 100, subject_id: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(limit)
    if subject_id:
        stmt = stmt.where(LedgerEntry.subject_id == subject_id)
    return [ledger_service.to_dict(e) for e in (await db.execute(stmt)).scalars().all()]


@router.get("/ledger/verify", summary="Re-compute the hash chain and report tampering")
async def ledger_verify(db: AsyncSession = Depends(get_db)):
    return await ledger_service.verify(db)
