"""
Automated tests for the deterministic Policy Engine.
Tests all 14+ policy scenarios from Section 22 of the spec.

Run:
    cd backend
    pytest tests/test_policy_engine.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.models.policy import PolicyDecision, PolicyContext, ConversationSignals
from app.policies.recovery_policy import evaluate_policy

# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_ctx(**kwargs) -> PolicyContext:
    """Create a PolicyContext with sensible defaults for testing."""
    defaults = dict(
        customer_id="CUS_TEST",
        amount_due=2499.0,
        payment_status="PAYMENT_FAILED",
        failure_reason="CARD_DECLINED",
        days_overdue=1,
        previous_attempts=0,
        call_attempts=0,
        payment_links_generated=0,
        has_active_payment_link=False,
        recovery_start_days=1,
        signals=ConversationSignals(
            customer_verified=True,
            willing_to_pay=True,
        ),
    )
    defaults.update(kwargs)
    return PolicyContext(**defaults)


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestPolicyEngine:

    def test_already_paid(self):
        """Rule 1: payment_status == PAID → STOP_PAID"""
        ctx = make_ctx(payment_status="PAID")
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_PAID
        assert result.should_stop is True
        assert result.can_create_payment_link is False

    def test_no_amount_due(self):
        """Rule 2: amount_due <= 0 → STOP_NO_DUE"""
        ctx = make_ctx(amount_due=0.0)
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_NO_DUE
        assert result.should_stop is True

    def test_no_amount_due_negative(self):
        """Rule 2: negative amount → STOP_NO_DUE"""
        ctx = make_ctx(amount_due=-100.0)
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_NO_DUE

    def test_unknown_customer(self):
        """Rule 3: unknown customer → ESCALATE"""
        ctx = make_ctx(signals=ConversationSignals(unknown_customer=True))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.should_escalate is True

    def test_contact_change_requested(self):
        """Rule 4: contact change → ESCALATE"""
        ctx = make_ctx(signals=ConversationSignals(
            customer_verified=True,
            contact_change_requested=True,
        ))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.should_escalate is True

    def test_invoice_dispute(self):
        """Rule 5: dispute raised → ESCALATE"""
        ctx = make_ctx(signals=ConversationSignals(
            customer_verified=True,
            dispute_raised=True,
        ))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.should_escalate is True
        assert result.can_create_payment_link is False

    def test_customer_refuses(self):
        """Rule 6: refused_to_pay → STOP_REFUSED"""
        ctx = make_ctx(signals=ConversationSignals(
            customer_verified=True,
            refused_to_pay=True,
        ))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_REFUSED
        assert result.should_stop is True

    def test_amount_mismatch(self):
        """Rule 7: customer states wrong amount → CLARIFY"""
        ctx = make_ctx(signals=ConversationSignals(
            customer_verified=True,
            willing_to_pay=True,
            amount_mismatch=True,
            customer_stated_amount=4999.0,
        ))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.CLARIFY
        assert result.can_create_payment_link is False

    def test_max_call_attempts_reached(self):
        """Rule 8: call_attempts >= MAX → STOP_MAX_ATTEMPTS"""
        ctx = make_ctx(call_attempts=2)  # MAX_CALL_ATTEMPTS = 2
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_MAX_ATTEMPTS
        assert result.should_stop is True

    def test_max_payment_links_reached(self):
        """Rule 8b: payment_links_generated >= MAX → STOP_MAX_ATTEMPTS"""
        ctx = make_ctx(payment_links_generated=2)  # MAX_PAYMENT_LINKS = 2
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_MAX_ATTEMPTS
        assert result.should_stop is True

    def test_recovery_window_expired(self):
        """Rule 9: recovery_start_days > MAX_RECOVERY_DAYS → STOP_WINDOW_EXPIRED"""
        ctx = make_ctx(recovery_start_days=8)  # MAX_RECOVERY_DAYS = 7
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_WINDOW_EXPIRED
        assert result.should_stop is True

    def test_promise_to_pay(self):
        """Rule 10: promise to pay → TRACK_PROMISE_TO_PAY"""
        ctx = make_ctx(signals=ConversationSignals(
            customer_verified=True,
            willing_to_pay=False,
            promise_to_pay=True,
            promise_date="2026-09-05",
        ))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.TRACK_PROMISE_TO_PAY
        assert result.can_create_payment_link is False

    def test_verified_willing_to_pay_card_declined(self):
        """Rule 11d: card declined + verified + willing → RECOVER_NOW"""
        ctx = make_ctx(
            amount_due=2499.0,
            payment_status="PAYMENT_FAILED",
            failure_reason="CARD_DECLINED",
            signals=ConversationSignals(
                customer_verified=True,
                willing_to_pay=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.RECOVER_NOW
        assert result.can_create_payment_link is True

    def test_checkout_abandoned_willing_to_pay(self):
        """Checkout abandoned + willing → RECOVER_NOW (within auto limit)"""
        ctx = make_ctx(
            amount_due=1500.0,
            payment_status="CHECKOUT_ABANDONED",
            failure_reason="CHECKOUT_ABANDONED",
            signals=ConversationSignals(
                customer_verified=True,
                willing_to_pay=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.RECOVER_NOW
        assert result.can_create_payment_link is True

    def test_existing_active_payment_link(self):
        """Rule 11a: active link exists → RESEND_EXISTING_LINK"""
        ctx = make_ctx(
            has_active_payment_link=True,
            signals=ConversationSignals(
                customer_verified=True,
                willing_to_pay=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.RESEND_EXISTING_LINK
        assert result.can_resend_payment_link is True
        assert result.can_create_payment_link is False

    def test_high_value_transaction_escalated(self):
        """Rule 11b: amount > 25000 → ESCALATE"""
        ctx = make_ctx(
            amount_due=75000.0,
            signals=ConversationSignals(
                customer_verified=True,
                willing_to_pay=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.should_escalate is True
        assert result.can_create_payment_link is False

    def test_medium_value_additional_verification(self):
        """Rule 11c: 5001 < amount <= 25000 → NEEDS_ADDITIONAL_VERIFICATION"""
        ctx = make_ctx(
            amount_due=15000.0,
            signals=ConversationSignals(
                customer_verified=True,
                willing_to_pay=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.NEEDS_ADDITIONAL_VERIFICATION
        assert result.can_create_payment_link is False

    def test_identity_mismatch_not_verified(self):
        """Identity mismatch: not verified → CLARIFY"""
        ctx = make_ctx(signals=ConversationSignals(
            customer_verified=False,
            willing_to_pay=True,
        ))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.CLARIFY

    def test_unknown_intent_unverified(self):
        """Unknown intent + not verified → CLARIFY"""
        ctx = make_ctx(signals=ConversationSignals())
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.CLARIFY

    def test_recovery_score_is_computed(self):
        """Recovery score should be a number between 0 and 100."""
        ctx = make_ctx()
        result = evaluate_policy(ctx)
        assert 0 <= result.recovery_score <= 100
        assert "Customer Intent" in result.score_breakdown

    def test_policy_checks_populated(self):
        """Policy checks list should be populated for transparency."""
        ctx = make_ctx()
        result = evaluate_policy(ctx)
        assert len(result.policy_checks) > 0
        assert all("label" in check for check in result.policy_checks)
        assert all("passed" in check for check in result.policy_checks)

    def test_paid_cannot_create_link_even_if_willing(self):
        """PAID status blocks payment link even with willing signals."""
        ctx = make_ctx(
            payment_status="PAID",
            signals=ConversationSignals(
                customer_verified=True,
                willing_to_pay=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.STOP_PAID
        assert result.can_create_payment_link is False

    def test_dispute_overrides_willingness(self):
        """Dispute should escalate even if customer says they're willing to pay."""
        ctx = make_ctx(signals=ConversationSignals(
            customer_verified=True,
            willing_to_pay=True,
            dispute_raised=True,
        ))
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.ESCALATE

    def test_subscription_payment_failed(self):
        """Subscription failure + verified + willing → RECOVER_NOW"""
        ctx = make_ctx(
            amount_due=999.0,
            payment_status="PAYMENT_FAILED",
            failure_reason="SUBSCRIPTION_PAYMENT_FAILED",
            signals=ConversationSignals(
                customer_verified=True,
                willing_to_pay=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.RECOVER_NOW
        assert result.can_create_payment_link is True

    def test_b2b_high_value_dispute(self):
        """B2B overdue invoice + dispute → ESCALATE"""
        ctx = make_ctx(
            amount_due=18500.0,
            payment_status="OVERDUE",
            signals=ConversationSignals(
                customer_verified=True,
                dispute_raised=True,
            ),
        )
        result = evaluate_policy(ctx)
        assert result.decision == PolicyDecision.ESCALATE
