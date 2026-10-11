from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.kb import KnowledgeBase
from app.engine.radar import SCENARIOS, WATCH_SOURCES, affected, content_hash, impact_set, scenario_dates
from app.models import Amendment, Notification, RegulatoryEvent, Regulation, SourceSnapshot, Standard, StandardStatus, Tender
from app.services import ledger_service
from app.services.tender_service import compile_tender

logger = logging.getLogger(__name__)


async def _apply_event_to_kb(db: AsyncSession, ev: Dict) -> Optional[str]:
    """Mutate the registry for an event. Returns a note."""
    eff = datetime.strptime(ev["effective_from"], "%Y-%m-%d") if ev.get("effective_from") else datetime.utcnow()
    subj = (await db.execute(select(Standard).where(Standard.is_number == ev["subject"]))).scalars().first()
    if ev["event_type"] == "amendment" and subj:
        n = 1 + max([a.amendment_number for a in (await db.execute(select(Amendment).where(Amendment.standard_id == subj.id))).scalars().all()] or [0])
        db.add(Amendment(standard_id=subj.id, amendment_number=n, title=ev["title"].replace("Amendment No. 4", f"Amendment No. {n}").replace("Amendment No. 1", f"Amendment No. {n}"),
                         published_at=datetime.utcnow(), effective_from=eff, changed_clauses=ev.get("changed_clauses"), summary=ev.get("summary")))
        return f"Amendment {n} registered for {subj.is_number}, effective {eff.date()}"
    if ev["event_type"] == "revision" and subj:
        new_no = ev["new_is_number"]
        if not (await db.execute(select(Standard).where(Standard.is_number == new_no))).scalars().first():
            db.add(Standard(is_number=new_no, title=ev["title"], scope=ev.get("summary"), status=StandardStatus.CURRENT,
                            edition="Simulated revision", division_code=subj.division_code, publication_date=datetime.utcnow(),
                            effective_from=eff, source_url="https://standards.bis.gov.in/"))
        subj.effective_to = eff - timedelta(days=1)
        subj.superseded_by = new_no
        return f"{new_no} registered; {subj.is_number} valid until {subj.effective_to.date()}"
    if ev["event_type"] in ("qco_new", "qco_amend"):
        key = f"SIM-{ev['subject'].replace(' ', '')}-{date.today().isoformat()}"
        if not (await db.execute(select(Regulation).where(Regulation.key == key))).scalars().first():
            db.add(Regulation(key=key, regulation_type="QCO", scheme="BIS Standard Mark (ISI) — Scheme-I", title=ev["title"],
                              issuing_authority="(simulated)", product_scope=ev.get("summary"), standard_ids=[ev["subject"]],
                              effective_from=eff, is_mandatory="yes", verification_state="simulated"))
        return f"Regulation {key} registered, effective {eff.date()}"
    return None


async def process_event(db: AsyncSession, ev: Dict, simulated: bool, actor: str = "radar") -> Dict:
    note = await _apply_event_to_kb(db, ev)
    event = RegulatoryEvent(event_type=ev["event_type"], subject=ev.get("subject"), title=ev["title"], summary=ev.get("summary"),
                            effective_from=ev.get("effective_from"), source_url=ev.get("source_url"), simulated=simulated, status="applied")
    db.add(event)
    await db.commit()
    await db.refresh(event)
    kb = await KnowledgeBase.from_db(db)
    imp = impact_set(kb, ev["subject"]) if ev.get("subject") else {"direct": [], "dependents": []}
    tenders = (await db.execute(select(Tender).where(Tender.twin.isnot(None), Tender.status.notin_(["archived", "closed"])))).scalars().all()
    hits = affected([{"tender_id": t.id, "title": t.title, "status": t.status, "twin": t.twin} for t in tenders], imp)
    results = []
    for h in hits:
        try:
            twin = await compile_tender(db, h["tender_id"], actor="radar", reason=f"regulatory event #{event.id}: {ev['title']}")
            delta = twin.get("delta", {})
            sev = "critical" if any(d["severity"] == "critical" for d in delta.get("introduced", [])) else ("warning" if delta.get("introduced") else "info")
            db.add(Notification(tender_id=h["tender_id"], event_id=event.id, severity=sev,
                                title=f"{ev['title']} affects “{h['title'][:60]}”",
                                message=f"{h['reason']}. Re-validated: {len(delta.get('introduced', []))} new finding(s), {len(delta.get('resolved', []))} resolved. "
                                        f"Readiness {delta.get('previous_score')} → {twin['readiness']['score']}.",
                                delta=delta))
            results.append({**h, "introduced": delta.get("introduced", []), "resolved": delta.get("resolved", []),
                            "readiness_before": delta.get("previous_score"), "readiness_after": twin["readiness"]["score"]})
        except Exception as e:
            logger.exception("revalidation failed")
            results.append({**h, "error": str(e)})
    event.impact = {"impact_set": imp, "affected": results, "kb_note": note}
    await db.commit()
    await ledger_service.append(db, actor, "regulatory_event.processed", "event", str(event.id),
                                {"title": ev["title"], "simulated": simulated, "impact_set": imp, "affected": [r["tender_id"] for r in results]})
    return {"event_id": event.id, "title": ev["title"], "simulated": simulated, "kb_change": note, "impact_set": imp, "affected_tenders": results}


async def simulate(db: AsyncSession, scenario: str) -> Dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario; choose one of {list(SCENARIOS)}")
    return await process_event(db, scenario_dates(scenario), simulated=True)


async def watch_sources(db: AsyncSession) -> Dict:
    import httpx
    out = []
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers={"User-Agent": "SpecSure-RegulatoryRadar/2.0 (+hackathon demo)"}) as client:
        for src in WATCH_SOURCES:
            status, h = "unreachable", None
            try:
                r = await client.get(src["url"])
                status, h = f"http {r.status_code}", content_hash(r.text)
            except Exception as e:
                status = f"unreachable: {e.__class__.__name__}"
            last = (await db.execute(select(SourceSnapshot).where(SourceSnapshot.key == src["key"]).order_by(SourceSnapshot.id.desc()).limit(1))).scalars().first()
            changed = bool(h and last and last.content_hash and last.content_hash != h)
            db.add(SourceSnapshot(key=src["key"], url=src["url"], content_hash=h, status=status))
            if changed:
                db.add(RegulatoryEvent(event_type="source_changed", subject=None, title=f"Official page changed: {src['label']}",
                                       summary="Content hash changed since the last check. A human must triage whether a standard/QCO changed.",
                                       source_url=src["url"], status="pending_triage"))
            out.append({**src, "status": status, "hash": h[:16] if h else None, "changed": changed, "first_seen": last is None})
    await db.commit()
    return {"checked": out, "note": "Changed pages create 'pending_triage' events; nothing is auto-applied to the registry."}
