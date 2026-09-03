"""
MongoDB async connection using Motor.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect_db():
    global _client
    try:
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
        # Verify connection
        await _client.admin.command("ping")
        logger.info("✅ Connected to MongoDB")
    except ConnectionFailure as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


async def close_db():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_db():
    if _client is None:
        raise RuntimeError("MongoDB not connected. Call connect_db() first.")
    return _client[settings.MONGODB_DB_NAME]


def get_collection(name: str):
    return get_db()[name]
