"""
Recovery API endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services import recovery_service
from app.models.policy import ConversationSignals

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


class EvaluateRequest(BaseModel):
    signals: ConversationSignals


class PromiseToPayRequest(BaseModel):
    promise_date: str   # YYYY-MM-DD
    amount: float


class EscalateRequest(BaseModel):
    reason: str


@router.post("/{customer_id}/start")
async def start_recovery(customer_id: str):
    """Start a recovery workflow for a customer."""
    customer = await recovery_service.start_recovery(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return {"message": "Recovery started", "customer": customer}


@router.post("/{customer_id}/evaluate")
async def evaluate_policy(customer_id: str, body: EvaluateRequest):
    """
    Run the deterministic policy engine.
    LLM-extracted signals are passed in; final decision is deterministic.
    """
    result = await recovery_service.evaluate_recovery_policy(customer_id, body.signals)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return result


@router.post("/{customer_id}/payment-link")
async def create_payment_link(customer_id: str):
    """
    Create a Razorpay payment link — ONLY if policy engine permits.
    Amount is always taken from MongoDB, not from customer or LLM.
    """
    result = await recovery_service.create_recovery_payment_link(customer_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    if "error" in result:
        raise HTTPException(status_code=403, detail=result)
    return result


@router.post("/{customer_id}/promise-to-pay")
async def record_promise(customer_id: str, body: PromiseToPayRequest):
    """Record a promise-to-pay commitment from the customer."""
    success = await recovery_service.record_promise_to_pay(
        customer_id, body.promise_date, body.amount
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return {"message": "Promise-to-pay recorded", "promise_date": body.promise_date}


@router.post("/{customer_id}/escalate")
async def escalate_recovery(customer_id: str, body: EscalateRequest):
    """Escalate a recovery case to human review."""
    success = await recovery_service.mark_escalated(customer_id, body.reason)
    if not success:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return {"message": "Case escalated", "reason": body.reason}
