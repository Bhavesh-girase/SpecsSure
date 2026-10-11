"""Regulatory Change Radar, QCO Impact Radar, notifications."""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine.kb import KnowledgeBase
from app.engine.radar import SCENARIOS, WATCH_SOURCES, affected, impact_set
from app.models import Notification, RegulatoryEvent, Tender
from app.services import radar_service

router = APIRouter()


@router.get("/radar/scenarios", summary="Simulation scenarios for the demo")
async def scenarios():
    return [{"key": k, "label": v["label"], "event_type": v["event_type"], "subject": v["subject"]} for k, v in SCENARIOS.items()]


@router.post("/radar/simulate/{scenario}", summary="Inject a SIMULATED regulatory event and re-validate affected tenders")
async def simulate(scenario: str, db: AsyncSession = Depends(get_db)):
    try:
        return await radar_service.simulate(db, scenario)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/radar/events", summary="Record a verified regulatory event (human-confirmed) and re-validate")
async def add_event(event_type: str = Body(...), subject: str = Body(...), title: str = Body(...), summary: Optional[str] = Body(None),
                    effective_from: Optional[str] = Body(None), source_url: Optional[str] = Body(None), new_is_number: Optional[str] = Body(None),
                    db: AsyncSession = Depends(get_db)):
    ev = {"event_type": event_type, "subject": subject, "title": title, "summary": summary, "effective_from": effective_from,
          "source_url": source_url, "new_is_number": new_is_number}
    return await radar_service.process_event(db, ev, simulated=False, actor="officer")


@router.get("/radar/events", summary="Regulatory event feed")
async def events(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(RegulatoryEvent).order_by(RegulatoryEvent.id.desc()).limit(100))).scalars().all()
    return [{"id": e.id, "event_type": e.event_type, "subject": e.subject, "title": e.title, "summary": e.summary,
             "effective_from": e.effective_from, "simulated": e.simulated, "status": e.status, "impact": e.impact,
             "source_url": e.source_url, "created_at": e.created_at.isoformat()} for e in rows]


@router.get("/radar/impact", summary="What-if: which active tenders depend on a standard (direct + via dependency graph)?")
async def impact(standard: str, db: AsyncSession = Depends(get_db)):
    kb = await KnowledgeBase.from_db(db)
    imp = impact_set(kb, standard)
    tenders = (await db.execute(select(Tender).where(Tender.twin.isnot(None)))).scalars().all()
    return {"standard": standard, "impact_set": imp,
            "affected": affected([{"tender_id": t.id, "title": t.title, "status": t.status, "twin": t.twin} for t in tenders], imp)}


@router.get("/radar/qco-impact", summary="QCO Impact Radar: tenders whose products fall under mandatory certification")
async def qco_impact(db: AsyncSession = Depends(get_db)):
    tenders = (await db.execute(select(Tender).where(Tender.twin.isnot(None)))).scalars().all()
    out = []
    for t in tenders:
        for dom, ds in (t.twin.get("domain_standards") or {}).items():
            for g in ds.get("regulations_in_force", []) + ds.get("regulations_upcoming", []):
                cert_missing = any(f["rule_id"] == "SS-CERT-001" and f.get("review_status", "open") == "open" for f in t.twin.get("findings", []))
                out.append({"tender_id": t.id, "tender": t.title, "domain": dom, "standard": ds.get("resolved"), "regulation": g["title"],
                            "effective_from": g.get("effective_from"), "upcoming": g in ds.get("regulations_upcoming", []),
                            "verification_state": g.get("verification_state"), "tender_requires_certification": not cert_missing})
    return out


@router.post("/radar/watch", summary="Poll official sources, hash-compare, raise triage events on change")
async def watch(db: AsyncSession = Depends(get_db)):
    return await radar_service.watch_sources(db)


@router.get("/radar/sources", summary="Watched official sources")
async def sources():
    return WATCH_SOURCES


@router.get("/notifications", summary="Notifications (revalidation results)")
async def notifications(unread_only: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(Notification).order_by(Notification.id.desc()).limit(100)
    if unread_only:
        stmt = stmt.where(Notification.read.is_(False))
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": n.id, "tender_id": n.tender_id, "event_id": n.event_id, "severity": n.severity, "title": n.title,
             "message": n.message, "delta": n.delta, "read": n.read, "created_at": n.created_at.isoformat()} for n in rows]


@router.post("/notifications/read", summary="Mark all notifications read")
async def mark_read(db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notification).values(read=True))
    await db.commit()
    return {"ok": True}
