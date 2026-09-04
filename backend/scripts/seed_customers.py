"""
Seed script: insert exactly 5 demo customers into MongoDB.
Idempotent — running multiple times will not create duplicates.

Usage:
    cd backend
    python scripts/seed_customers.py
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Allow running from backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "revenue_recovery")

NOW = datetime.now(timezone.utc)


CUSTOMERS = [
    # ─── Customer 1: Successful recovery candidate ───────────────────────────
    {
        "customer_id": "CUS_001",
        "name": "Rahul Sharma",
        "contact": {
            "phone": "+91-9094211133",
            "email": "rooooot0101010101@gmail.com",
        },
        "invoice_id": "INV_001",
        "amount_due": 2499.0,
        "payment_status": "PAYMENT_FAILED",
        "failure_reason": "CARD_DECLINED",
        "days_overdue": 1,
        "previous_attempts": 1,
        "dispute": False,
        "risk_level": "HIGH",
        "recovery_state": {
            "status": "NOT_STARTED",
            "call_attempts": 0,
            "payment_links_generated": 0,
            "reminders_sent": 0,
            "recovery_start_date": None,
            "last_action": None,
            "last_action_at": None,
            "current_decision": None,
            "current_decision_reason": None,
            "customer_intent": None,
            "customer_verified": False,
            "dispute_raised": False,
            "contact_change_requested": False,
            "promise_to_pay": None,
            "payment_links": [],
            "amount_recovered": 0.0,
            "recovery_score": None,
            "escalated": False,
            "escalation_reason": None,
        },
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        # EXPECTED: Verified + willing + low amount → CREATE PAYMENT LINK
    },

    # ─── Customer 2: Promise to Pay scenario ─────────────────────────────────
    {
        "customer_id": "CUS_002",
        "name": "Priya Mehta",
        "contact": {
            "phone": "+91-9876500002",
            "email": "priya.mehta.test@example.com",
        },
        "invoice_id": "INV_002",
        "amount_due": 4999.0,
        "payment_status": "OVERDUE",
        "failure_reason": "NONE",
        "days_overdue": 5,
        "previous_attempts": 1,
        "dispute": False,
        "risk_level": "MEDIUM",
        "recovery_state": {
            "status": "NOT_STARTED",
            "call_attempts": 0,
            "payment_links_generated": 0,
            "reminders_sent": 0,
            "recovery_start_date": None,
            "last_action": None,
            "last_action_at": None,
            "current_decision": None,
            "current_decision_reason": None,
            "customer_intent": None,
            "customer_verified": False,
            "dispute_raised": False,
            "contact_change_requested": False,
            "promise_to_pay": None,
            "payment_links": [],
            "amount_recovered": 0.0,
            "recovery_score": None,
            "escalated": False,
            "escalation_reason": None,
        },
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        # EXPECTED: "Abhi nahi, kal salary aayegi" → TRACK_PROMISE_TO_PAY
    },

    # ─── Customer 3: Invoice Dispute ─────────────────────────────────────────
    {
        "customer_id": "CUS_003",
        "name": "Amit Enterprises",
        "contact": {
            "phone": "+91-9876500003",
            "email": "amit.enterprises.test@example.com",
        },
        "invoice_id": "INV_003",
        "amount_due": 18500.0,
        "payment_status": "OVERDUE",
        "failure_reason": "NONE",
        "days_overdue": 17,
        "previous_attempts": 2,
        "dispute": False,  # Dispute will be raised during conversation
        "risk_level": "HIGH",
        "recovery_state": {
            "status": "NOT_STARTED",
            "call_attempts": 0,
            "payment_links_generated": 0,
            "reminders_sent": 0,
            "recovery_start_date": None,
            "last_action": None,
            "last_action_at": None,
            "current_decision": None,
            "current_decision_reason": None,
            "customer_intent": None,
            "customer_verified": False,
            "dispute_raised": False,
            "contact_change_requested": False,
            "promise_to_pay": None,
            "payment_links": [],
            "amount_recovered": 0.0,
            "recovery_score": None,
            "escalated": False,
            "escalation_reason": None,
        },
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        # EXPECTED: "Ye invoice galat hai" → ESCALATE (no payment link)
    },

    # ─── Customer 4: Already Paid ─────────────────────────────────────────────
    {
        "customer_id": "CUS_004",
        "name": "Neha Joshi",
        "contact": {
            "phone": "+91-9876500004",
            "email": "neha.joshi.test@example.com",
        },
        "invoice_id": "INV_004",
        "amount_due": 1999.0,
        "payment_status": "PAID",
        "failure_reason": "NONE",
        "days_overdue": 0,
        "previous_attempts": 0,
        "dispute": False,
        "risk_level": "LOW",
        "recovery_state": {
            "status": "STOPPED_PAID",
            "call_attempts": 0,
            "payment_links_generated": 0,
            "reminders_sent": 0,
            "recovery_start_date": None,
            "last_action": "STOP_PAID",
            "last_action_at": NOW.isoformat(),
            "current_decision": "STOP_PAID",
            "current_decision_reason": "Invoice already paid",
            "customer_intent": None,
            "customer_verified": False,
            "dispute_raised": False,
            "contact_change_requested": False,
            "promise_to_pay": None,
            "payment_links": [],
            "amount_recovered": 1999.0,
            "recovery_score": None,
            "escalated": False,
            "escalation_reason": None,
        },
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        # EXPECTED: payment_status == PAID → STOP_PAID (no new payment link)
    },

    # ─── Customer 5: High Value / Human Escalation ────────────────────────────
    {
        "customer_id": "CUS_005",
        "name": "Arjun Kapoor",
        "contact": {
            "phone": "+91-9876500005",
            "email": "arjun.kapoor.test@example.com",
        },
        "invoice_id": "INV_005",
        "amount_due": 75000.0,
        "payment_status": "PAYMENT_FAILED",
        "failure_reason": "PAYMENT_METHOD_FAILED",
        "days_overdue": 2,
        "previous_attempts": 1,
        "dispute": False,
        "risk_level": "CRITICAL",
        "recovery_state": {
            "status": "NOT_STARTED",
            "call_attempts": 0,
            "payment_links_generated": 0,
            "reminders_sent": 0,
            "recovery_start_date": None,
            "last_action": None,
            "last_action_at": None,
            "current_decision": None,
            "current_decision_reason": None,
            "customer_intent": None,
            "customer_verified": False,
            "dispute_raised": False,
            "contact_change_requested": False,
            "promise_to_pay": None,
            "payment_links": [],
            "amount_recovered": 0.0,
            "recovery_score": None,
            "escalated": False,
            "escalation_reason": None,
        },
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        # EXPECTED: ₹75,000 > HIGH_VALUE_THRESHOLD → ESCALATE (no auto payment link)
    },
]


async def seed():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    col = db["customers"]

    print(f"🔗 Connecting to MongoDB: {MONGODB_DB_NAME}")

    inserted = 0
    updated = 0

    for customer in CUSTOMERS:
        # Idempotent: update if exists, insert if not
        result = await col.update_one(
            {"customer_id": customer["customer_id"]},
            {"$setOnInsert": customer},
            upsert=True,
        )
        if result.upserted_id:
            print(f"  ✅ Inserted: {customer['customer_id']} — {customer['name']}")
            inserted += 1
        else:
            print(f"  ⏭️  Already exists: {customer['customer_id']} — {customer['name']} (skipped)")
            updated += 1

    # Seed sample audit events for Neha (already paid)
    audit_col = db["audit_events"]
    existing_audit = await audit_col.count_documents({"customer_id": "CUS_004"})
    if existing_audit == 0:
        await audit_col.insert_many([
            {
                "customer_id": "CUS_004",
                "invoice_id": "INV_004",
                "event": "PAYMENT_RECEIVED",
                "amount": 1999.0,
                "actor": "SYSTEM",
                "reason": "Payment completed via UPI",
                "metadata": {"razorpay_payment_id": "pay_test_sample001"},
                "timestamp": (NOW - timedelta(days=1)).isoformat(),
            },
            {
                "customer_id": "CUS_004",
                "invoice_id": "INV_004",
                "event": "REVENUE_RECOVERED",
                "amount": 1999.0,
                "actor": "SYSTEM",
                "reason": "Revenue recovered: ₹1,999",
                "metadata": None,
                "timestamp": (NOW - timedelta(days=1)).isoformat(),
            },
        ])
        print("  ✅ Sample audit events seeded for CUS_004")

    print(f"\n🌱 Seeding complete: {inserted} inserted, {updated} already existed")
    print(f"\nCustomers in database:")
    async for c in col.find({}, {"customer_id": 1, "name": 1, "payment_status": 1, "amount_due": 1, "_id": 0}):
        print(f"  {c['customer_id']} | {c['name']:25s} | {c['payment_status']:20s} | ₹{c['amount_due']:,.0f}")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
