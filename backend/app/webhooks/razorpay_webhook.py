"""
Razorpay Webhook endpoint.
ALWAYS verify webhook signature before processing.
NEVER mark a customer as paid unless this webhook confirms it.
"""
import json
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from app.services.razorpay_service import verify_webhook_signature
from app.services import recovery_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
):
    """
    Handle Razorpay webhook events.
    Processes: payment_link.paid
    """
    body = await request.body()

    # Step 1: Verify signature
    if x_razorpay_signature:
        if not verify_webhook_signature(body, x_razorpay_signature):
            logger.warning("⚠️  Invalid Razorpay webhook signature")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        logger.warning("⚠️  No webhook signature header present")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    logger.info(f"📨 Razorpay webhook received: {event}")

    # Step 2: Handle payment_link.paid
    if event == "payment_link.paid":
        await _handle_payment_link_paid(payload)

    # Step 3: Handle payment.captured (as fallback)
    elif event == "payment.captured":
        await _handle_payment_captured(payload)

    return {"status": "ok", "event": event}


async def _handle_payment_link_paid(payload: dict):
    """Process a payment_link.paid event."""
    try:
        entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

        link_id = entity.get("id")
        notes = entity.get("notes", {})
        customer_id = notes.get("customer_id")
        invoice_id = notes.get("invoice_id")

        amount_paid = entity.get("amount_paid", 0) / 100  # Convert paise to INR
        razorpay_payment_id = payment_entity.get("id", "")

        if not customer_id or not invoice_id:
            logger.error(f"❌ Webhook: missing customer_id/invoice_id in notes: {notes}")
            return

        logger.info(f"💰 Payment confirmed: {customer_id} | ₹{amount_paid} | link={link_id}")

        success = await recovery_service.handle_payment_success(
            customer_id=customer_id,
            invoice_id=invoice_id,
            link_id=link_id,
            amount_paid=amount_paid,
            razorpay_payment_id=razorpay_payment_id,
        )

        if success:
            logger.info(f"✅ Revenue recovered: ₹{amount_paid:,.0f} for {customer_id}")
        else:
            logger.error(f"❌ Failed to update recovery state for {customer_id}")

    except Exception as e:
        logger.error(f"❌ Error processing payment_link.paid: {e}", exc_info=True)


async def _handle_payment_captured(payload: dict):
    """Process a payment.captured event (fallback)."""
    try:
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes = entity.get("notes", {})
        customer_id = notes.get("customer_id")
        invoice_id = notes.get("invoice_id")
        
        if not customer_id:
            return  # Not one of our recovery payments
        
        amount_paid = entity.get("amount", 0) / 100
        payment_id = entity.get("id", "")

        await recovery_service.handle_payment_success(
            customer_id=customer_id,
            invoice_id=invoice_id or "",
            link_id=notes.get("link_id", ""),
            amount_paid=amount_paid,
            razorpay_payment_id=payment_id,
        )

    except Exception as e:
        logger.error(f"❌ Error processing payment.captured: {e}", exc_info=True)
