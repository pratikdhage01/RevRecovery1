"""
Pydantic models for all database entities.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    OVERDUE = "OVERDUE"
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    CANCELLED = "CANCELLED"
    CHECKOUT_ABANDONED = "CHECKOUT_ABANDONED"


class FailureReason(str, Enum):
    CARD_DECLINED = "CARD_DECLINED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    PAYMENT_METHOD_FAILED = "PAYMENT_METHOD_FAILED"
    CHECKOUT_ABANDONED = "CHECKOUT_ABANDONED"
    SUBSCRIPTION_PAYMENT_FAILED = "SUBSCRIPTION_PAYMENT_FAILED"
    NETWORK_ERROR = "NETWORK_ERROR"
    BANK_DECLINED = "BANK_DECLINED"
    NONE = "NONE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecoveryStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    CALLING = "CALLING"
    PROMISE_TO_PAY = "PROMISE_TO_PAY"
    ESCALATED = "ESCALATED"
    RECOVERED = "RECOVERED"
    STOPPED_PAID = "STOPPED_PAID"
    STOPPED_NO_DUE = "STOPPED_NO_DUE"
    STOPPED_MAX_ATTEMPTS = "STOPPED_MAX_ATTEMPTS"
    STOPPED_WINDOW_EXPIRED = "STOPPED_WINDOW_EXPIRED"
    REFUSED = "REFUSED"


class AuditEventType(str, Enum):
    RECOVERY_STARTED = "RECOVERY_STARTED"
    CUSTOMER_VERIFIED = "CUSTOMER_VERIFIED"
    PAYMENT_CONTEXT_RETRIEVED = "PAYMENT_CONTEXT_RETRIEVED"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    PAYMENT_LINK_CREATED = "PAYMENT_LINK_CREATED"
    PAYMENT_LINK_SENT = "PAYMENT_LINK_SENT"
    PAYMENT_LINK_RESENT = "PAYMENT_LINK_RESENT"
    PROMISE_TO_PAY_RECORDED = "PROMISE_TO_PAY_RECORDED"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    REVENUE_RECOVERED = "REVENUE_RECOVERED"
    RECOVERY_STOPPED = "RECOVERY_STOPPED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"
    CONTACT_CHANGE_BLOCKED = "CONTACT_CHANGE_BLOCKED"
    DISPUTE_DETECTED = "DISPUTE_DETECTED"
    RECOVERY_REFUSED = "RECOVERY_REFUSED"
    CALL_STARTED = "CALL_STARTED"
    CALL_ENDED = "CALL_ENDED"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class ContactInfo(BaseModel):
    phone: str
    email: str


class PromiseToPay(BaseModel):
    promise_date: str          # YYYY-MM-DD
    amount: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    fulfilled: bool = False
    fulfillment_date: Optional[str] = None


class PaymentLinkRecord(BaseModel):
    link_id: str               # Razorpay payment link ID
    short_url: str
    amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "created"    # created | paid | cancelled | expired


class RecoveryState(BaseModel):
    status: RecoveryStatus = RecoveryStatus.NOT_STARTED
    call_attempts: int = 0
    payment_links_generated: int = 0
    reminders_sent: int = 0
    recovery_start_date: Optional[datetime] = None
    last_action: Optional[str] = None
    last_action_at: Optional[datetime] = None
    current_decision: Optional[str] = None
    current_decision_reason: Optional[str] = None
    customer_intent: Optional[str] = None  # willing_to_pay | refusing | unknown | promise_to_pay
    customer_verified: bool = False
    dispute_raised: bool = False
    contact_change_requested: bool = False
    promise_to_pay: Optional[PromiseToPay] = None
    payment_links: List[PaymentLinkRecord] = Field(default_factory=list)
    amount_recovered: float = 0.0
    recovery_score: Optional[int] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Main DB models
# ---------------------------------------------------------------------------

class Customer(BaseModel):
    customer_id: str           # e.g. CUS_001
    name: str
    contact: ContactInfo
    invoice_id: str            # e.g. INV_001
    amount_due: float          # INR
    payment_status: PaymentStatus
    failure_reason: FailureReason = FailureReason.NONE
    days_overdue: int = 0
    previous_attempts: int = 0
    dispute: bool = False
    risk_level: RiskLevel = RiskLevel.MEDIUM
    recovery_state: RecoveryState = Field(default_factory=RecoveryState)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class AuditEvent(BaseModel):
    customer_id: str
    invoice_id: str
    event: AuditEventType
    amount: Optional[float] = None
    actor: str = "AI_AGENT"    # AI_AGENT | SYSTEM | HUMAN
    reason: Optional[str] = None
    metadata: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
