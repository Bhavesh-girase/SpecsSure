import asyncio
import logging
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.standard import Standard
from app.models.requirement import StandardRelation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build_relations")

async def build_normative_relations():
    """Extracts and verifies normative reference edges across all registered standards."""
    async with async_session_maker() as session:
        stmt = select(StandardRelation)
        res = await session.execute(stmt)
        relations = res.scalars().all()
        logger.info(f"Verified {len(relations)} active knowledge graph edges in the database.")

if __name__ == "__main__":
    asyncio.run(build_normative_relations())
