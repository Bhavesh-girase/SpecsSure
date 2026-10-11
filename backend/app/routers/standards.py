from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.db.session import get_db
from app.models.standard import Standard, StandardStatus
from app.models.amendment import Amendment
from app.models.requirement import StandardRelation
from app.schemas.standard import StandardRead, StandardGraphResponse
from app.services.graph_service import graph_service

router = APIRouter()

@router.get("/standards", response_model=List[StandardRead], summary="List and filter standards")
async def list_standards(
    search: Optional[str] = Query(None, description="Search keyword in IS number or title"),
    status: Optional[str] = Query(None, description="Filter by status (current, superseded, etc.)"),
    division: Optional[str] = Query(None, description="Filter by BIS division code (e.g. CED, MTD, ETD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Lists standards with optional filtering by status, division, or keyword search."""
    stmt = (
        select(Standard)
        .options(selectinload(Standard.amendments), selectinload(Standard.outgoing_relations))
        .offset(skip)
        .limit(limit)
    )

    if status:
        stmt = stmt.where(Standard.status == status)
    if division:
        stmt = stmt.where(Standard.division_code.ilike(f"%{division}%"))
    if search:
        stmt = stmt.where(
            or_(
                Standard.is_number.ilike(f"%{search}%"),
                Standard.title.ilike(f"%{search}%"),
                Standard.scope.ilike(f"%{search}%")
            )
        )

    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/standards/{is_number}", response_model=StandardRead, summary="Get standard details")
async def get_standard_detail(
    is_number: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves full specification details, revisions, and active amendments for a single IS standard."""
    stmt = (
        select(Standard)
        .options(selectinload(Standard.amendments), selectinload(Standard.outgoing_relations))
        .where(Standard.is_number.ilike(f"%{is_number.strip()}%"))
    )
    res = await db.execute(stmt)
    std = res.scalars().first()
    if not std:
        raise HTTPException(status_code=404, detail=f"Standard '{is_number}' not found in registry.")
    return std

@router.get("/standards/{is_number}/graph", response_model=StandardGraphResponse, summary="Get relationship graph")
async def get_standard_graph(
    is_number: str,
    depth: int = Query(2, ge=1, le=3, description="Graph expansion depth (1 to 3 hops)"),
    db: AsyncSession = Depends(get_db)
):
    """Returns knowledge graph centered on the standard (normative references, test methods, safety codes)."""
    graph_res = await graph_service.get_standard_graph(is_number=is_number, db=db, depth=depth)
    if not graph_res:
        raise HTTPException(status_code=404, detail=f"Standard '{is_number}' not found.")
    return graph_res
