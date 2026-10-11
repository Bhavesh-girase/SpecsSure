from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.standard import Standard
from app.models.product_ontology import ProductCategory
from app.config import settings

router = APIRouter()

@router.get("/health", summary="Health check and status")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint providing system status and database metrics."""
    try:
        stmt_std = select(func.count(Standard.id))
        res_std = await db.execute(stmt_std)
        total_standards = res_std.scalar() or 0

        stmt_cat = select(func.count(ProductCategory.id))
        res_cat = await db.execute(stmt_cat)
        total_categories = res_cat.scalar() or 0

        db_status = "connected"
    except Exception as e:
        total_standards = 0
        total_categories = 0
        db_status = f"degraded: {str(e)}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": db_status,
        "total_standards": total_standards,
        "total_product_categories": total_categories,
        "embedding_model": settings.EMBEDDING_MODEL,
        "reranker_model": settings.RERANKER_MODEL
    }
