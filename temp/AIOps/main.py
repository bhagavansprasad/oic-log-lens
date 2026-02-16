# =============================================================
# AIOps Platform — FastAPI Application
# Entry point: uvicorn main:app --reload
# =============================================================

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config.settings import load_config
from db.connection import OracleConnectionPool
from services.semantic_text_builder import SemanticTextBuilder
from services.embedding_service import EmbeddingService
from services.oracle_semantic_repository import OracleSemanticRepository
from services.aiops_service import AIOpsService
from api.routes import router
from api.dependencies import set_service

# ------------------------------------------------------------------ #
# Logging
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Lifespan — startup & shutdown
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise all components on startup.
    Cleanly shut down pool on exit.
    """
    logger.info("AIOps Platform starting up...")
    start = time.perf_counter()

    cfg = load_config()

    # Oracle pool
    pool = OracleConnectionPool(cfg.oracle)
    pool.init()

    # Gemini embedding service
    embedding_svc = EmbeddingService(cfg.gemini)
    embedding_svc.init()

    # Wire up AIOpsService
    service = AIOpsService(
        builder            = SemanticTextBuilder(),
        embedding_svc      = embedding_svc,
        repository         = OracleSemanticRepository(pool),
        threshold_known    = cfg.threshold_known,
        threshold_related  = cfg.threshold_related,
    )

    # Make service available to routes via dependency
    set_service(service)

    elapsed = (time.perf_counter() - start) * 1000
    logger.info("AIOps Platform ready | startup_ms=%.1f", elapsed)

    yield  # app is running

    # Shutdown
    logger.info("AIOps Platform shutting down...")
    pool.close()


# ------------------------------------------------------------------ #
# App
# ------------------------------------------------------------------ #
app = FastAPI(
    title       = "AIOps Semantic Error Intelligence Platform",
    description = "Semantic similarity matching for IT operations error logs",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.include_router(router)


# ------------------------------------------------------------------ #
# Health check
# ------------------------------------------------------------------ #
@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "aiops-platform"}
