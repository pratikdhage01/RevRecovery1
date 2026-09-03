"""
DETERMINISTIC POLICY ENGINE
============================
This module makes ALL recovery decisions.
The LLM CANNOT override these decisions.
The LLM only provides structured conversation signals (ConversationSignals).
The final authority is always this deterministic engine.

Policy Rules (in priority order):
  1.  PAID → STOP_PAID
  2.  No amount due → STOP_NO_DUE
  3.  Unknown customer → ESCALATE
  4.  Contact change requested → ESCALATE
  5.  Dispute raised → ESCALATE
  6.  Customer refused → STOP_REFUSED
  7.  Amount mismatch → CLARIFY
  8.  Max attempts reached → STOP_MAX_ATTEMPTS
  9.  Recovery window expired → STOP_WINDOW_EXPIRED
  10. Customer verified + willing to pay → evaluate amount tier
      a. Existing active link → RESEND_EXISTING_LINK
      b. Amount > HIGH_VALUE_THRESHOLD → ESCALATE (human)
      c. Amount > AUTO_RECOVERY_LIMIT → NEEDS_ADDITIONAL_VERIFICATION
      d. Amount within auto limit → RECOVER_NOW
  11. Promise to pay → TRACK_PROMISE_TO_PAY
  12. Not verified → CLARIFY
"""

from typing import List, Tuple
from app.models.policy import (
    PolicyContext,
    PolicyDecision,
    PolicyResult,
    ConversationSignals,
)
from app.core.config import settings


# ---------------------------------------------------------------------------
# Recovery Score Computation (transparent + deterministic)
# ---------------------------------------------------------------------------

def compute_recovery_score(ctx: PolicyContext) -> Tuple[int, dict]:
    """
    Compute a 0-100 recovery score based on deterministic factors.
    Returns (total_score, score_breakdown).
    """
    breakdown = {}

    # Customer Intent (0–30)
    if ctx.signals.willing_to_pay:
        intent_score = 30
    elif ctx.signals.promise_to_pay:
        intent_score = 15
    elif ctx.signals.refused_to_pay:
        intent_score = 0
    elif ctx.signals.dispute_raised:
        intent_score = 0
    else:
        intent_score = 10  # Unknown intent
    breakdown["Customer Intent"] = f"{intent_score}/30"

    # Payment History (0–20)
    if ctx.previous_attempts == 0:
        history_score = 20
    elif ctx.previous_attempts == 1:
        history_score = 15
    elif ctx.previous_attempts == 2:
        history_score = 8
    else:
        history_score = 0
    breakdown["Payment History"] = f"{history_score}/20"

    # Verification (0–20)
    if ctx.signals.customer_verified and not ctx.signals.dispute_raised:
        verification_score = 20
    elif ctx.signals.customer_verified:
        verification_score = 5
    else:
        verification_score = 0
    breakdown["Verification"] = f"{verification_score}/20"

    # Amount Risk (0–15)
    if ctx.amount_due <= settings.AUTO_RECOVERY_LIMIT:
        amount_score = 15
    elif ctx.amount_due <= settings.HIGH_VALUE_THRESHOLD:
        amount_score = 8
    else:
        amount_score = 0
    breakdown["Amount Risk"] = f"{amount_score}/15"

    # Recovery Window (0–15)
    if ctx.days_overdue <= 3:
        window_score = 15
    elif ctx.days_overdue <= 7:
        window_score = 10
    elif ctx.days_overdue <= 14:
        window_score = 5
    else:
        window_score = 0
    breakdown["Recovery Window"] = f"{window_score}/15"

    total = intent_score + history_score + verification_score + amount_score + window_score
    breakdown["TOTAL"] = f"{total}/100"

    return total, breakdown


# ---------------------------------------------------------------------------
# Policy Check Helpers
# ---------------------------------------------------------------------------

def _check(label: str, passed: bool, reason: str = "") -> dict:
    return {"label": label, "passed": passed, "reason": reason}


# ---------------------------------------------------------------------------
# Core Policy Engine
# ---------------------------------------------------------------------------

def evaluate_policy(ctx: PolicyContext) -> PolicyResult:
    """
    Run all policy rules in priority order.
    Returns a PolicyResult with a final decision that CANNOT be overridden by LLM.
    """
    checks: List[dict] = []

    # ─── Rule 1: Already Paid ────────────────────────────────────────────────
    if ctx.payment_status == "PAID":
        checks.append(_check("Payment Status", False, "Already paid"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.STOP_PAID,
            reason="Invoice is already paid. No further recovery action needed.",
            should_stop=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Payment Status", True, "Not paid"))

    # ─── Rule 2: No Amount Due ───────────────────────────────────────────────
    if ctx.amount_due <= 0:
        checks.append(_check("Amount Due", False, "No amount outstanding"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.STOP_NO_DUE,
            reason="No amount is due. Recovery not applicable.",
            should_stop=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Amount Due", True, f"₹{ctx.amount_due:,.0f} outstanding"))

    # ─── Rule 3: Unknown Customer ────────────────────────────────────────────
    if ctx.signals.unknown_customer:
        checks.append(_check("Customer Identity", False, "Customer not found in database"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.ESCALATE,
            reason="Customer identity could not be established. Cannot proceed with automated recovery.",
            should_escalate=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )

    # ─── Rule 4: Contact Change ──────────────────────────────────────────────
    if ctx.signals.contact_change_requested:
        checks.append(_check("Contact Safety", False, "Contact change request detected"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.ESCALATE,
            reason="Contact change requested. Cannot modify registered contact without human verification.",
            should_escalate=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Contact Safety", True, "No contact change requested"))

    # ─── Rule 5: Invoice Dispute ─────────────────────────────────────────────
    if ctx.signals.dispute_raised:
        checks.append(_check("No Dispute", False, "Customer disputes the invoice"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.ESCALATE,
            reason="Customer raised an invoice dispute. Automated recovery stopped. Human review required.",
            should_escalate=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("No Dispute", True, "No dispute raised"))

    # ─── Rule 6: Customer Refused ────────────────────────────────────────────
    if ctx.signals.refused_to_pay:
        checks.append(_check("Customer Willing", False, "Customer explicitly refused payment"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.STOP_REFUSED,
            reason="Customer explicitly refused to pay. Recovery stopped respectfully. Refusal recorded.",
            should_stop=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Customer Willing", True, "No explicit refusal"))

    # ─── Rule 7: Amount Mismatch ─────────────────────────────────────────────
    if ctx.signals.amount_mismatch:
        checks.append(_check("Amount Verified", False, "Customer stated incorrect amount"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.CLARIFY,
            reason=(
                f"Amount mismatch detected. Database shows ₹{ctx.amount_due:,.0f} "
                f"but customer stated ₹{ctx.signals.customer_stated_amount or 'unknown'}. "
                "Cannot create payment link until amount is clarified."
            ),
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Amount Verified", True, f"Amount ₹{ctx.amount_due:,.0f} confirmed"))

    # ─── Rule 8: Max Attempts ────────────────────────────────────────────────
    if ctx.call_attempts >= settings.MAX_CALL_ATTEMPTS:
        checks.append(_check("Call Attempts", False, f"{ctx.call_attempts}/{settings.MAX_CALL_ATTEMPTS} attempts used"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.STOP_MAX_ATTEMPTS,
            reason=f"Maximum call attempts ({settings.MAX_CALL_ATTEMPTS}) reached. Stopping automated recovery.",
            should_stop=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Call Attempts", True, f"{ctx.call_attempts}/{settings.MAX_CALL_ATTEMPTS} attempts used"))

    if ctx.payment_links_generated >= settings.MAX_PAYMENT_LINKS:
        checks.append(_check("Payment Links", False, f"{ctx.payment_links_generated}/{settings.MAX_PAYMENT_LINKS} links used"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.STOP_MAX_ATTEMPTS,
            reason=f"Maximum payment links ({settings.MAX_PAYMENT_LINKS}) already generated.",
            should_stop=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Payment Links", True, f"{ctx.payment_links_generated}/{settings.MAX_PAYMENT_LINKS} links used"))

    # ─── Rule 9: Recovery Window ─────────────────────────────────────────────
    if ctx.recovery_start_days > settings.MAX_RECOVERY_DAYS:
        checks.append(_check("Recovery Window", False, f"Day {ctx.recovery_start_days}/{settings.MAX_RECOVERY_DAYS}"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.STOP_WINDOW_EXPIRED,
            reason=f"Recovery window of {settings.MAX_RECOVERY_DAYS} days has expired.",
            should_stop=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )
    checks.append(_check("Recovery Window", True, f"Day {ctx.recovery_start_days}/{settings.MAX_RECOVERY_DAYS}"))

    # ─── Rule 10: Promise to Pay ─────────────────────────────────────────────
    if ctx.signals.promise_to_pay and not ctx.signals.willing_to_pay:
        checks.append(_check("Promise to Pay", True, f"Promised date: {ctx.signals.promise_date}"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.TRACK_PROMISE_TO_PAY,
            reason=f"Customer committed to pay on {ctx.signals.promise_date}. Recording promise. No immediate payment link.",
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )

    # ─── Rules 11+: Verified + Willing ──────────────────────────────────────
    if ctx.signals.customer_verified and ctx.signals.willing_to_pay:
        checks.append(_check("Customer Verified", True, "Identity confirmed"))
        checks.append(_check("Willing to Pay", True, "Customer expressed payment intent"))

        # Rule 11a: Existing active link
        if ctx.has_active_payment_link:
            checks.append(_check("Existing Link", True, "Active payment link found"))
            score, breakdown = compute_recovery_score(ctx)
            return PolicyResult(
                decision=PolicyDecision.RESEND_EXISTING_LINK,
                reason="Customer is verified and willing to pay. Active payment link already exists — resending instead of creating a duplicate.",
                can_resend_payment_link=True,
                recovery_score=score,
                score_breakdown=breakdown,
                policy_checks=checks,
            )
        checks.append(_check("No Duplicate Link", True, "No active link exists"))

        # Rule 11b: High value → escalate
        if ctx.amount_due > settings.HIGH_VALUE_THRESHOLD:
            checks.append(_check("Amount Within Auto Limit", False, f"₹{ctx.amount_due:,.0f} > ₹{settings.HIGH_VALUE_THRESHOLD:,.0f} high-value threshold"))
            score, breakdown = compute_recovery_score(ctx)
            return PolicyResult(
                decision=PolicyDecision.ESCALATE,
                reason=(
                    f"Amount ₹{ctx.amount_due:,.0f} exceeds high-value threshold ₹{settings.HIGH_VALUE_THRESHOLD:,.0f}. "
                    "Human review required before automated payment link creation."
                ),
                should_escalate=True,
                recovery_score=score,
                score_breakdown=breakdown,
                policy_checks=checks,
            )

        # Rule 11c: Medium value → extra verification
        if ctx.amount_due > settings.AUTO_RECOVERY_LIMIT:
            checks.append(_check("Amount Within Auto Limit", False, f"₹{ctx.amount_due:,.0f} > ₹{settings.AUTO_RECOVERY_LIMIT:,.0f} auto-limit; additional verification needed"))
            score, breakdown = compute_recovery_score(ctx)
            return PolicyResult(
                decision=PolicyDecision.NEEDS_ADDITIONAL_VERIFICATION,
                reason=(
                    f"Amount ₹{ctx.amount_due:,.0f} requires additional verification "
                    f"(auto-recovery limit: ₹{settings.AUTO_RECOVERY_LIMIT:,.0f})."
                ),
                recovery_score=score,
                score_breakdown=breakdown,
                policy_checks=checks,
            )

        # Rule 11d: Within auto limit → RECOVER NOW
        checks.append(_check("Amount Within Auto Limit", True, f"₹{ctx.amount_due:,.0f} ≤ ₹{settings.AUTO_RECOVERY_LIMIT:,.0f}"))
        score, breakdown = compute_recovery_score(ctx)
        return PolicyResult(
            decision=PolicyDecision.RECOVER_NOW,
            reason=(
                f"Customer verified, willing to pay, no dispute, amount within auto-recovery limit. "
                f"Creating Razorpay payment link for ₹{ctx.amount_due:,.0f}."
            ),
            can_create_payment_link=True,
            recovery_score=score,
            score_breakdown=breakdown,
            policy_checks=checks,
        )

    # ─── Fallback: Not verified ──────────────────────────────────────────────
    if not ctx.signals.customer_verified:
        checks.append(_check("Customer Verified", False, "Identity not yet confirmed"))
    if not ctx.signals.willing_to_pay:
        checks.append(_check("Willing to Pay", False, "Payment intent not confirmed"))

    score, breakdown = compute_recovery_score(ctx)
    return PolicyResult(
        decision=PolicyDecision.CLARIFY,
        reason="Need to verify customer identity and confirm payment intent before proceeding.",
        recovery_score=score,
        score_breakdown=breakdown,
        policy_checks=checks,
    )
