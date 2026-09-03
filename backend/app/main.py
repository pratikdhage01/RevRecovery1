"""
FastAPI application entrypoint.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.mongodb import connect_db, close_db
from app.api.customers import router as customers_router
from app.api.recovery import router as recovery_router
from app.api.dashboard import router as dashboard_router
from app.api.livekit_token import router as livekit_router
from app.webhooks.razorpay_webhook import router as webhook_router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 Starting AI Revenue Recovery Agent backend...")
    await connect_db()
    yield
    logger.info("Shutting down...")
    await close_db()


app = FastAPI(
    title="AI Revenue Recovery Agent",
    description="Razorpay Track 03 — AI-powered revenue recovery with LiveKit voice agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(customers_router)
app.include_router(recovery_router)
app.include_router(dashboard_router)
app.include_router(livekit_router)
app.include_router(webhook_router)


@app.get("/")
async def root():
    return {
        "name": "AI Revenue Recovery Agent",
        "version": "1.0.0",
        "status": "running",
        "track": "Razorpay Track 03",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
