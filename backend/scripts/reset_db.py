"""
Reset script: Clears all customers and audit events, then re-seeds fresh data.

Usage:
    cd backend
    python scripts/reset_db.py
"""
import asyncio
import io
import os
import sys
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows consoles
if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from scripts.seed_customers import seed

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "revenue_recovery")


async def reset(reseed: bool = True):
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]

    print(f"[RESET] Clearing collections in database '{MONGODB_DB_NAME}'...")
    del_cust = await db.customers.delete_many({})
    del_audit = await db.audit_events.delete_many({})
    print(f"  - Deleted {del_cust.deleted_count} customer documents.")
    print(f"  - Deleted {del_audit.deleted_count} audit event documents.")
    client.close()

    print("[SUCCESS] Database wiped clean.\n")

    if reseed:
        print("[SEED] Re-seeding clean initial data...")
        await seed()


if __name__ == "__main__":
    asyncio.run(reset(reseed=True))
