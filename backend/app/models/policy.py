"""
Pydantic models for Policy Engine inputs/outputs.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class PolicyDecision(str, Enum):
    """All possible recovery policy decisions."""
    RECOVER_NOW = "RECOVER_NOW"
    RESEND_EXISTING_LINK = "RESEND_EXISTING_LINK"
    ALTERNATIVE_RECOVERY = "ALTERNATIVE_RECOVERY"
    CLARIFY = "CLARIFY"
    TRACK_PROMISE_TO_PAY = "TRACK_PROMISE_TO_PAY"
    ESCALATE = "ESCALATE"
    STOP_PAID = "STOP_PAID"
    STOP_NO_DUE = "STOP_NO_DUE"
    STOP_MAX_ATTEMPTS = "STOP_MAX_ATTEMPTS"
    STOP_WINDOW_EXPIRED = "STOP_WINDOW_EXPIRED"
    STOP_REFUSED = "STOP_REFUSED"
    NEEDS_ADDITIONAL_VERIFICATION = "NEEDS_ADDITIONAL_VERIFICATION"


class ConversationSignals(BaseModel):
    """
    Structured signals extracted by LLM from conversation.
    These are INPUTS to the deterministic policy engine.
    The policy engine makes the final decision — not the LLM.
    """
    customer_verified: bool = False          # Customer confirmed identity/context
    willing_to_pay: bool = False             # Customer expressed intent to pay
    dispute_raised: bool = False             # Customer disputes invoice/amount
    contact_change_requested: bool = False   # Customer asked to change contact
    promise_to_pay: bool = False             # Customer promised to pay later
    promise_date: Optional[str] = None       # YYYY-MM-DD if promise_to_pay
    refused_to_pay: bool = False             # Customer explicitly refused
    amount_mismatch: bool = False            # Customer stated wrong amount
    customer_stated_amount: Optional[float] = None
    unknown_customer: bool = False           # Customer not found in DB
    reason_given: Optional[str] = None       # Why they can't pay now


class PolicyContext(BaseModel):
    """
    Full context passed to the Policy Engine.
    Combines database facts + conversation signals.
    """
    # Database facts (authoritative — from MongoDB)
    customer_id: str
    amount_due: float
    payment_status: str
    failure_reason: str
    days_overdue: int
    previous_attempts: int
    call_attempts: int
    payment_links_generated: int
    has_active_payment_link: bool
    recovery_start_days: int = 0    # How many days ago recovery started

    # Conversation signals (from LLM extraction)
    signals: ConversationSignals = ConversationSignals()


class PolicyResult(BaseModel):
    """Structured output from the Policy Engine."""
    decision: PolicyDecision
    reason: str
    can_create_payment_link: bool = False
    can_resend_payment_link: bool = False
    should_escalate: bool = False
    should_stop: bool = False
    recovery_score: int = 0
    score_breakdown: dict = {}
    policy_checks: list = []   # List of passed/failed checks for UI display
