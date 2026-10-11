import asyncio
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.ledger import GENESIS, entry_hash, payload_hash, verify_chain
from app.models import LedgerEntry

_lock = asyncio.Lock()


async def append(db: AsyncSession, actor: str, action: str, subject_type: str, subject_id: str, payload: Dict, commit: bool = True) -> Dict:
    async with _lock:
        last = (await db.execute(select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(1))).scalars().first()
        seq = (last.seq + 1) if last else 1
        prev = last.entry_hash if last else GENESIS
        ts = datetime.now(timezone.utc).isoformat()
        ph = payload_hash(payload)
        eh = entry_hash(prev, seq, ts, actor, action, subject_type, str(subject_id), ph)
        e = LedgerEntry(seq=seq, ts=ts, actor=actor, action=action, subject_type=subject_type, subject_id=str(subject_id),
                        payload=payload, payload_hash=ph, prev_hash=prev, entry_hash=eh)
        db.add(e)
        if commit:
            await db.commit()
        return {"seq": seq, "entry_hash": eh}


def to_dict(e: LedgerEntry) -> Dict:
    return {"seq": e.seq, "ts": e.ts, "actor": e.actor, "action": e.action, "subject_type": e.subject_type,
            "subject_id": e.subject_id, "payload": e.payload, "payload_hash": e.payload_hash, "prev_hash": e.prev_hash,
            "entry_hash": e.entry_hash}


async def verify(db: AsyncSession) -> Dict:
    rows = (await db.execute(select(LedgerEntry).order_by(LedgerEntry.seq))).scalars().all()
    return verify_chain([to_dict(r) for r in rows])
