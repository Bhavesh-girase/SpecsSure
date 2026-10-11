"""Procurement Knowledge Graph API — explore, query as-of a date, explain paths, impact, export (Neo4j / JSON-LD)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import studio_service

router = APIRouter()


def _d(s: Optional[str]) -> date:
    return date.fromisoformat(s) if s else date.today()


@router.get("/kg/stats", summary="Node / edge counts by type and KB snapshot")
async def stats(db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    return kg.stats()


@router.get("/kg/search", summary="Find nodes (items, standards, regulations, policies, parameters)")
async def search(q: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    return kg.search(q, limit)


@router.get("/kg/node", summary="Node details + neighbourhood (as of a date)")
async def node(id: str, depth: int = 1, as_of: Optional[str] = None, limit: int = 80, db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    n = kg.node(id)
    if n is None:
        raise HTTPException(404, "node not found")
    return {"node": n, "graph": kg.neighbourhood(id, max(1, min(depth, 3)), _d(as_of), limit=limit),
            "impacted_items": kg.impacted_items(id) if id.startswith(("std:", "fam:", "reg:")) else []}


@router.get("/kg/items/{item_id}", summary="Everything a tender for this item must respect, as of a date (with KG paths)")
async def item_bundle(item_id: str, as_of: Optional[str] = None, horizon_days: int = 180, db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    try:
        return kg.bundle(item_id, _d(as_of), horizon_days)
    except KeyError:
        raise HTTPException(404, "unknown item")


@router.get("/kg/path", summary="Explain how two nodes are connected")
async def path(a: str, b: str, db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    return {"steps": kg.explain_path(a, b)}


@router.get("/kg/impact", summary="Items affected if a standard / regulation changes (reverse traversal)")
async def impact(node: str, db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    return {"node": node, "items": kg.impacted_items(node)}


@router.get("/kg/export.cypher", response_class=PlainTextResponse, summary="Export the graph as Cypher (Neo4j)")
async def export_cypher(db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    return PlainTextResponse(kg.export_cypher(), headers={"Content-Disposition": 'attachment; filename="specsure_pkg.cypher"'})


@router.get("/kg/export.jsonld", summary="Export the graph as JSON-LD")
async def export_jsonld(db: AsyncSession = Depends(get_db)):
    kg = await studio_service.kg_for(db)
    return kg.export_jsonld()
