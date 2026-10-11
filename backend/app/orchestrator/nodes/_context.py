from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

# Context holder for current async database session during graph execution
db_session: Optional[AsyncSession] = None

def set_db_session(session: AsyncSession):
    global db_session
    db_session = session

def get_db_session() -> AsyncSession:
    global db_session
    if db_session is None:
        raise RuntimeError("Database session was not initialized in orchestrator context.")
    return db_session
