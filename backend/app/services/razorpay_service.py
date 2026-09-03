"""
Razorpay API service wrapper (Test Mode only).
Uses httpx for direct API calls to avoid pkg_resources issues on Python 3.13.
All communication with Razorpay happens here — never in frontend.
"""
import httpx
import hmac
import hashlib
import base64
import json
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"


def _get_auth_header() -> str:
    """Basic Auth header for Razorpay API."""
    credentials = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def _headers() -> dict:
    return {
        "Authorization": _get_auth_header(),
        "Content-Type": "application/json",
    }


async def create_payment_link(
    customer_id: str,
    invoice_id: str,
    amount: float,
    customer_name: str,
    customer_phone: str,
    customer_email: str,
    description: str = "Payment Recovery",
) -> dict:
    """
    Create a Razorpay Payment Link (Test Mode).
    Amount is taken from MongoDB — NOT from customer's verbal statement.
    """
    # Razorpay amount is in paise (1 INR = 100 paise)
    amount_paise = int(amount * 100)

    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": description,
        "customer": {
            "name": customer_name,
            "contact": customer_phone,
            "email": customer_email,
        },
        "notify": {
            "sms": False,   # Test mode — disable actual SMS
            "email": False,  # Test mode — disable actual email
        },
        "reminder_enable": False,
        "notes": {
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "created_by": "AI_REVENUE_RECOVERY_AGENT",
        },
        "callback_url": f"{settings.FRONTEND_URL}/payment-success",
        "callback_method": "get",
    }

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        # Return a mock response in development without keys
        logger.warning("⚠️  No Razorpay credentials — returning mock payment link")
        return {
            "id": f"plink_mock_{customer_id}",
            "short_url": f"https://rzp.io/l/mock-{customer_id}",
            "amount": amount_paise,
            "status": "created",
            "notes": payload["notes"],
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RAZORPAY_BASE_URL}/payment_links",
                headers=_headers(),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            link = response.json()
            logger.info(f"✅ Payment link created: {link['id']} for {customer_id}")
            return link
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Razorpay API error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create payment link for {customer_id}: {e}")
        raise


async def get_payment_link(link_id: str) -> dict:
    """Fetch payment link status from Razorpay."""
    if not settings.RAZORPAY_KEY_ID:
        return {"id": link_id, "status": "created"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{RAZORPAY_BASE_URL}/payment_links/{link_id}",
            headers=_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


async def cancel_payment_link(link_id: str) -> dict:
    """Cancel an existing payment link."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RAZORPAY_BASE_URL}/payment_links/{link_id}/cancel",
            headers=_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify Razorpay webhook signature using HMAC-SHA256.
    ALWAYS verify before processing webhook events.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("⚠️  RAZORPAY_WEBHOOK_SECRET not set — skipping verification (dev mode)")
        return True  # Allow in development without secret

    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
