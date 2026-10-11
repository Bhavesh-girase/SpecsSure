"""Standards intelligence tools: temporal engine, equivalence, formal verification playground, memory, rules."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine import equivalence
from app.engine.compiler import compile_ir
from app.engine.docparse import parse_text
from app.engine.kb import KnowledgeBase
from app.engine.linter import rules_catalog
from app.engine.sarif import to_sarif
from app.engine.temporal import resolve
from app.engine.tender_ir import build_ir
from app.models import Review
from app.services import ledger_service
from app.services.tender_service import memory_for

router = APIRouter()


@router.get("/temporal/resolve", summary="As-of-date resolution of a standard citation (edition, amendments, QCOs in force)")
async def temporal_resolve(citation: str, as_of: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    kb = await KnowledgeBase.from_db(db)
    return resolve(kb, citation, date.fromisoformat(as_of) if as_of else date.today()).to_dict()


@router.get("/temporal/timeline", summary="Edition timeline of a standard family")
async def temporal_timeline(citation: str, db: AsyncSession = Depends(get_db)):
    kb = await KnowledgeBase.from_db(db)
    r = resolve(kb, citation, date.today())
    rec = kb.lookup(citation)
    amends = [a.to_dict() for e in kb.by_family.get(r.family, []) for a in kb.amendments_of(e.id)]
    regs = [g.to_dict() for g in kb.regulations_for_family(r.family)]
    return {"family": r.family, "editions": r.timeline, "amendments": amends, "regulations": regs, "current": r.in_force}


@router.get("/equivalence/standards", summary="Standards with machine-readable requirement sets")
async def equivalence_list():
    return equivalence.available()


@router.get("/equivalence", summary="Compare two standards/grades parameter-by-parameter (never auto-concludes equivalence)")
async def equivalence_compare(a: str, b: str, grade_a: Optional[str] = None, grade_b: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    kb = await KnowledgeBase.from_db(db)
    res = equivalence.compare(a, b, grade_a, grade_b, kb)
    if "error" in res:
        raise HTTPException(404, res)
    return res


@router.post("/reviews", summary="Record a human decision (equivalence approval, restriction justification, ...)")
async def add_review(subject_type: str = Body(...), subject_id: str = Body(...), decision: str = Body(...),
                     reviewer: str = Body("Technical committee"), comment: Optional[str] = Body(None), data: Optional[dict] = Body(None),
                     db: AsyncSession = Depends(get_db)):
    r = Review(subject_type=subject_type, subject_id=subject_id, decision=decision, reviewer=reviewer, comment=comment, data=data)
    db.add(r)
    await db.commit()
    await ledger_service.append(db, reviewer, f"{subject_type}.review", subject_type, subject_id, {"decision": decision, "comment": comment})
    return {"id": r.id, "decision": decision}


@router.get("/reviews", summary="Human decisions")
async def list_reviews(subject_type: Optional[str] = None, subject_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    stmt = select(Review).order_by(Review.id.desc())
    if subject_type:
        stmt = stmt.where(Review.subject_type == subject_type)
    if subject_id:
        stmt = stmt.where(Review.subject_id == subject_id)
    return [{"id": r.id, "subject_type": r.subject_type, "subject_id": r.subject_id, "decision": r.decision, "reviewer": r.reviewer,
             "comment": r.comment, "created_at": r.created_at.isoformat()} for r in (await db.execute(stmt)).scalars().all()]


@router.post("/lint", summary="Stateless tender lint (paste text → findings, twin, SARIF). Nothing is stored.")
async def lint_text(text: str = Body(..., embed=True), as_of: Optional[str] = Body(None, embed=True), sarif: bool = Body(False, embed=True),
                    db: AsyncSession = Depends(get_db)):
    kb = await KnowledgeBase.from_db(db)
    tw = compile_ir(build_ir(parse_text(text, "pasted.txt"), doc_type="tender"), kb, as_of=date.fromisoformat(as_of) if as_of else None)
    return to_sarif(tw) if sarif else tw


@router.get("/rules", summary="Tender Linter rule catalogue")
async def rules():
    return rules_catalog()


@router.get("/memory/search", summary="Institutional memory: similar historical clauses & tenders")
async def memory_search(q: str = Query(..., min_length=3), db: AsyncSession = Depends(get_db)):
    mem = await memory_for(db)
    return {"clause_precedents": mem.clause_precedents(q, k=5, min_score=0.15), "similar_tenders": mem.similar_tenders(q, k=5),
            "recurring_patterns": mem.recurring_patterns()}
