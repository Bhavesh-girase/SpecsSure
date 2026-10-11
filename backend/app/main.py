import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.db.init_db import init_db
from app.routers import analyze, standards, search, health, tenders, bids, radar, intel, governance, demo, studio, kg, marketplace, lifecycle, corpus

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SpecSure")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} backend...")
    await init_db()
    try:
        from scripts.seed_standards_database import seed_all_if_needed
        await seed_all_if_needed()
    except Exception as e:
        logger.warning(f"Auto-seed notice: {e}")
    if settings.SEED_DEMO:
        try:
            from app.db.session import async_session_maker
            from app.routers.demo import seed_demo
            async with async_session_maker() as db:
                ids = await seed_demo(db)
                logger.info(f"Demo data ready: {ids}")
        except Exception as e:
            logger.warning(f"Demo seed notice: {e}")
    # warm the Indian Standards corpus + its embedding model in the background so the first search is fast
    import threading

    def _warm():
        try:
            from app.services.corpus_service import corpus_model, get_corpus
            c = get_corpus()
            if c.emb is not None:
                corpus_model()
            logger.info(f"Standards corpus ready: {len(c.catalogue)} designations, {len(c.graph)} parsed")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Corpus warm-up notice: {e}")
    threading.Thread(target=_warm, daemon=True).start()
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME} backend.")


app = FastAPI(
    title="SpecSure — Tender Intelligence & Standards Compliance",
    description=(
        "Evidence-first tender compiler for Indian public procurement: Tender Digital Twin, formal (SMT) contradiction proofs, "
        "temporal standards engine, QCO radar, market-restriction evidence, corrigendum merge, pre-bid prediction, "
        "Bid Mirror compliance matrix and verifiable Product Compliance Passports."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
app.add_middleware(GZipMiddleware, minimum_size=2048)

for r, tag in [(health, "Health"), (analyze, "Standards Recommendation"), (standards, "Standards Registry"), (search, "Search"),
               (tenders, "Buyer — Tender Digital Twin"), (bids, "Bidder — Bid Mirror & Passport"), (radar, "Regulatory Radar"),
               (intel, "Standards Intelligence"), (governance, "Governance & Audit"), (studio, "Buyer — Tender Studio (intent → tender)"),
               (kg, "Procurement Knowledge Graph"), (marketplace, "Contractor — Marketplace, Bid Form & Match Index"),
               (lifecycle, "Lifecycle — Queries, Evaluation, Award & Dashboards"),
               (corpus, "Standards Recommender — full Indian Standards corpus"), (demo, "Demo")]:
    app.include_router(r.router, prefix="/api/v1", tags=[tag])


@app.get("/", tags=["Root"])
async def root():
    return {"message": "SpecSure — Tender Intelligence & Standards Compliance platform (SIH PS-108).", "docs": "/docs",
            "version": settings.VERSION, "health": "/api/v1/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
