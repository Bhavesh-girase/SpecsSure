import logging
from sqlalchemy import text, inspect
from app.db.session import engine, Base
import app.models  # noqa: F401  (registers all tables)

logger = logging.getLogger(__name__)


def _add_missing_columns(sync_conn):
    """Tiny forward-only auto-migration: add columns that exist in the models but not in the database.
    Keeps existing docker volumes working after upgrades (Alembic remains available for real migrations)."""
    insp = inspect(sync_conn)
    existing_tables = set(insp.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in have:
                continue
            ddl_type = col.type.compile(dialect=sync_conn.dialect)
            sync_conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl_type}'))
            logger.info("Auto-migration: added column %s.%s", table.name, col.name)


async def init_db():
    logger.info("Initializing SpecSure database tables and extensions...")
    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception as e:
                logger.warning(f"pgvector extension notice: {e}")
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.run_sync(_add_missing_columns)
        except Exception as e:
            logger.warning(f"Auto-migration skipped: {e}")
    logger.info("SpecSure database initialized successfully.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
