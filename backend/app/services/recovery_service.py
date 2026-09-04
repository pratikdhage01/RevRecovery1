"""
Recovery orchestration service.
Coordinates customer lookup, policy evaluation, Razorpay actions, and audit logging.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

from app.database.mongodb import get_collection
from app.models.customer import (
    Customer, RecoveryState, AuditEvent, AuditEventType,
    RecoveryStatus, PaymentStatus, PaymentLinkRecord, PromiseToPay
)
from app.models.policy import PolicyContext, PolicyResult, ConversationSignals
from app.policies.recovery_policy import evaluate_policy
from app.services import razorpay_service, email_service
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_customer(customer_id: str) -> Optional[dict]:
    """Fetch customer from MongoDB by customer_id."""
    col = get_collection("customers")
    return await col.find_one({"customer_id": customer_id}, {"_id": 0})


async def get_all_customers() -> list:
    """Fetch all customers."""
    col = get_collection("customers")
    cursor = col.find({}, {"_id": 0})
    return await cursor.to_list(length=100)


async def log_audit_event(event: AuditEvent):
    """Write an audit event to MongoDB."""
    col = get_collection("audit_events")
    await col.insert_one(event.model_dump())
    logger.info(f"📋 Audit: [{event.event}] customer={event.customer_id}")


async def get_audit_trail(customer_id: str) -> list:
    """Fetch all audit events for a customer, newest first."""
    col = get_collection("audit_events")
    cursor = col.find({"customer_id": customer_id}, {"_id": 0}).sort("timestamp", -1)
    return await cursor.to_list(length=200)


async def update_customer_recovery(customer_id: str, updates: dict):
    """Update customer recovery state fields."""
    col = get_collection("customers")
    updates["updated_at"] = datetime.now(timezone.utc)
    await col.update_one(
        {"customer_id": customer_id},
        {"$set": updates}
    )


async def get_dashboard_stats() -> dict:
    """Compute aggregate dashboard statistics."""
    col = get_collection("customers")
    customers = await col.find({}, {"_id": 0}).to_list(length=500)
    
    total_at_risk = sum(
        c["amount_due"] for c in customers
        if c["payment_status"] not in ("PAID", "CANCELLED")
    )
    total_recovered = sum(
        c.get("recovery_state", {}).get("amount_recovered", 0)
        for c in customers
    )
    active_recoveries = sum(
        1 for c in customers
        if c.get("recovery_state", {}).get("status") in (
            "IN_PROGRESS", "CALLING", "PROMISE_TO_PAY"
        )
    )
    customers_contacted = sum(
        1 for c in customers
        if c.get("recovery_state", {}).get("call_attempts", 0) > 0
    )
    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0

    return {
        "revenue_at_risk": round(total_at_risk, 2),
        "revenue_recovered": round(total_recovered, 2),
        "recovery_rate": round(recovery_rate, 1),
        "active_recoveries": active_recoveries,
        "customers_contacted": customers_contacted,
        "total_customers": len(customers),
    }


async def start_recovery(customer_id: str) -> Optional[dict]:
    """Mark a recovery as started and log the event."""
    customer = await get_customer(customer_id)
    if not customer:
        return None

    now = datetime.now(timezone.utc)
    await update_customer_recovery(customer_id, {
        "recovery_state.status": RecoveryStatus.IN_PROGRESS,
        "recovery_state.recovery_start_date": now,
        "recovery_state.call_attempts": customer.get("recovery_state", {}).get("call_attempts", 0) + 1,
        "recovery_state.last_action": "CALL_STARTED",
        "recovery_state.last_action_at": now,
    })

    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=customer["invoice_id"],
        event=AuditEventType.RECOVERY_STARTED,
        amount=customer["amount_due"],
        actor="SYSTEM",
        reason="Recovery call initiated from dashboard",
    ))

    return await get_customer(customer_id)


async def evaluate_recovery_policy(
    customer_id: str,
    signals: ConversationSignals
) -> Optional[dict]:
    """
    Run the deterministic policy engine for a customer.
    Returns PolicyResult as dict.
    """
    customer = await get_customer(customer_id)
    if not customer:
        return None

    rs = customer.get("recovery_state", {})
    
    # Check if there's an active (unpaid) payment link
    payment_links = rs.get("payment_links", [])
    has_active_link = any(
        pl.get("status") == "created" for pl in payment_links
    )

    # Calculate recovery window days
    start_date = rs.get("recovery_start_date")
    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        elif isinstance(start_date, datetime) and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        recovery_days = (datetime.now(timezone.utc) - start_date).days
    else:
        recovery_days = 0

    ctx = PolicyContext(
        customer_id=customer_id,
        amount_due=customer["amount_due"],
        payment_status=customer["payment_status"],
        failure_reason=customer.get("failure_reason", "NONE"),
        days_overdue=customer.get("days_overdue", 0),
        previous_attempts=customer.get("previous_attempts", 0),
        call_attempts=rs.get("call_attempts", 0),
        payment_links_generated=rs.get("payment_links_generated", 0),
        has_active_payment_link=has_active_link,
        recovery_start_days=recovery_days,
        signals=signals,
    )

    result = evaluate_policy(ctx)

    # Save decision to DB
    now = datetime.now(timezone.utc)
    await update_customer_recovery(customer_id, {
        "recovery_state.current_decision": result.decision,
        "recovery_state.current_decision_reason": result.reason,
        "recovery_state.recovery_score": result.recovery_score,
        "recovery_state.customer_intent": (
            "willing_to_pay" if signals.willing_to_pay else
            "promise_to_pay" if signals.promise_to_pay else
            "refusing" if signals.refused_to_pay else
            "dispute" if signals.dispute_raised else
            "unknown"
        ),
        "recovery_state.customer_verified": signals.customer_verified,
        "recovery_state.dispute_raised": signals.dispute_raised,
        "recovery_state.contact_change_requested": signals.contact_change_requested,
        "recovery_state.last_action": f"POLICY_EVALUATED:{result.decision}",
        "recovery_state.last_action_at": now,
    })

    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=customer["invoice_id"],
        event=AuditEventType.POLICY_EVALUATED,
        amount=customer["amount_due"],
        actor="AI_AGENT",
        reason=result.reason,
        metadata={"decision": result.decision, "score": result.recovery_score},
    ))

    return result.model_dump()


async def create_recovery_payment_link(customer_id: str) -> Optional[dict]:
    """
    Create a Razorpay payment link — ONLY if policy engine allows it.
    Amount is ALWAYS taken from MongoDB, never from conversation.
    """
    customer = await get_customer(customer_id)
    if not customer:
        return None

    rs = customer.get("recovery_state", {})
    
    # Safety: re-evaluate policy before creating link
    signals = ConversationSignals(
        customer_verified=rs.get("customer_verified", False),
        willing_to_pay=rs.get("customer_intent") == "willing_to_pay",
        dispute_raised=rs.get("dispute_raised", False),
    )
    
    result = await evaluate_recovery_policy(customer_id, signals)
    if not result or not result.get("can_create_payment_link"):
        return {
            "error": "Policy engine did not authorize payment link creation.",
            "decision": result.get("decision") if result else "UNKNOWN",
            "reason": result.get("reason") if result else "Policy check failed.",
        }

    # Create link with DB amount
    link = await razorpay_service.create_payment_link(
        customer_id=customer_id,
        invoice_id=customer["invoice_id"],
        amount=customer["amount_due"],  # ← Always from DB
        customer_name=customer["name"],
        customer_phone=customer["contact"]["phone"],
        customer_email=customer["contact"]["email"],
        description=f"Payment recovery for invoice {customer['invoice_id']}",
    )

    short_url: str = str(link.get("short_url") or link.get("id") or "")

    link_record = {
        "link_id": link["id"],
        "short_url": short_url,
        "amount": customer["amount_due"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "created",
    }

    # Update customer record
    now = datetime.now(timezone.utc)
    col = get_collection("customers")
    await col.update_one(
        {"customer_id": customer_id},
        {
            "$push": {"recovery_state.payment_links": link_record},
            "$inc": {"recovery_state.payment_links_generated": 1},
            "$set": {
                "recovery_state.status": RecoveryStatus.IN_PROGRESS,
                "recovery_state.last_action": "PAYMENT_LINK_CREATED",
                "recovery_state.last_action_at": now,
                "updated_at": now,
            }
        }
    )

    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=customer["invoice_id"],
        event=AuditEventType.PAYMENT_LINK_CREATED,
        amount=customer["amount_due"],
        actor="AI_AGENT",
        reason="Policy engine authorized payment link creation",
        metadata={"link_id": link["id"], "short_url": short_url},
    ))

    # Dispatch payment link email if customer email and short_url are present
    customer_email = customer.get("contact", {}).get("email")
    if customer_email and short_url:
        try:
            await email_service.send_payment_link_email(
                to_email=customer_email,
                customer_name=customer.get("name", "Valued Customer"),
                invoice_id=customer.get("invoice_id", ""),
                amount=customer["amount_due"],
                payment_link=short_url,
            )
        except Exception as exc:
            logger.warning(f"Could not send payment link email to {customer_email}: {exc}")

    return {
        "link_id": link["id"],
        "short_url": short_url,
        "amount": customer["amount_due"],
        "customer_name": customer["name"],
    }


async def record_promise_to_pay(customer_id: str, promise_date: str, amount: float) -> bool:
    """Record a customer's promise-to-pay commitment."""
    customer = await get_customer(customer_id)
    if not customer:
        return False

    ptp = {
        "promise_date": promise_date,
        "amount": amount,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "fulfilled": False,
    }
    
    now = datetime.now(timezone.utc)
    await update_customer_recovery(customer_id, {
        "recovery_state.status": RecoveryStatus.PROMISE_TO_PAY,
        "recovery_state.promise_to_pay": ptp,
        "recovery_state.customer_intent": "promise_to_pay",
        "recovery_state.last_action": "PROMISE_TO_PAY_RECORDED",
        "recovery_state.last_action_at": now,
    })

    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=customer["invoice_id"],
        event=AuditEventType.PROMISE_TO_PAY_RECORDED,
        amount=amount,
        actor="AI_AGENT",
        reason=f"Customer promised to pay on {promise_date}",
        metadata={"promise_date": promise_date},
    ))
    return True


async def mark_escalated(customer_id: str, reason: str) -> bool:
    """Mark a customer as escalated to human."""
    customer = await get_customer(customer_id)
    if not customer:
        return False

    now = datetime.now(timezone.utc)
    await update_customer_recovery(customer_id, {
        "recovery_state.status": RecoveryStatus.ESCALATED,
        "recovery_state.escalated": True,
        "recovery_state.escalation_reason": reason,
        "recovery_state.last_action": "ESCALATED",
        "recovery_state.last_action_at": now,
    })

    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=customer["invoice_id"],
        event=AuditEventType.ESCALATED_TO_HUMAN,
        amount=customer["amount_due"],
        actor="AI_AGENT",
        reason=reason,
    ))
    return True


async def handle_payment_success(
    customer_id: str,
    invoice_id: str,
    link_id: str,
    amount_paid: float,
    razorpay_payment_id: str,
) -> bool:
    """
    Handle a confirmed payment from Razorpay webhook.
    ONLY mark as paid when Razorpay webhook confirms it — never on LLM claim.
    """
    customer = await get_customer(customer_id)
    if not customer:
        return False

    now = datetime.now(timezone.utc)
    col = get_collection("customers")
    
    # Update payment link status
    await col.update_one(
        {"customer_id": customer_id, "recovery_state.payment_links.link_id": link_id},
        {"$set": {"recovery_state.payment_links.$.status": "paid"}}
    )

    # Mark as recovered
    await col.update_one(
        {"customer_id": customer_id},
        {
            "$set": {
                "payment_status": PaymentStatus.PAID,
                "recovery_state.status": RecoveryStatus.RECOVERED,
                "recovery_state.amount_recovered": amount_paid,
                "recovery_state.last_action": "PAYMENT_RECEIVED",
                "recovery_state.last_action_at": now,
                "updated_at": now,
            }
        }
    )

    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=invoice_id,
        event=AuditEventType.PAYMENT_RECEIVED,
        amount=amount_paid,
        actor="SYSTEM",
        reason="Payment confirmed via Razorpay webhook",
        metadata={"razorpay_payment_id": razorpay_payment_id, "link_id": link_id},
    ))

    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=invoice_id,
        event=AuditEventType.REVENUE_RECOVERED,
        amount=amount_paid,
        actor="SYSTEM",
        reason=f"Revenue recovered: ₹{amount_paid:,.0f}",
    ))

    logger.info(f"💰 Revenue recovered: ₹{amount_paid:,.0f} for {customer_id}")
    return True
