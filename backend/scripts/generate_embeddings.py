import asyncio
import logging
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.standard import Standard
from app.services.embedding_service import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate_embeddings")

async def generate_missing_embeddings():
    """Generates dense semantic embeddings for standards that do not have them."""
    async with async_session_maker() as session:
        stmt = select(Standard).where(Standard.embedding.is_(None))
        res = await session.execute(stmt)
        standards = res.scalars().all()

        if not standards:
            logger.info("All standards already possess computed vector embeddings.")
            return

        logger.info(f"Generating embeddings for {len(standards)} standards...")
        
        # Batch encode in chunks of 32
        for i in range(0, len(standards), 32):
            batch = standards[i:i+32]
            passages = [
                f"{std.is_number} — {std.title} — {(std.scope or '')[:500]}"
                for std in batch
            ]
            embeddings = embedding_service.embed_batch(passages, is_query=False)
            
            for j, std in enumerate(batch):
                std.embedding = embeddings[j]
                std.search_text = f"{std.is_number} {std.title} {std.scope or ''} {std.division_code or ''}"
                
            await session.commit()
            logger.info(f"Embedded batch {i+1} to {min(i+32, len(standards))}")

    logger.info("Embedding generation completed successfully.")

if __name__ == "__main__":
    asyncio.run(generate_missing_embeddings())
