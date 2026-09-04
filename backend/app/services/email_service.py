"""
SMTP Email Service — sends payment link notifications to customers.
Uses Python's built-in smtplib (no extra dependencies).
Supports Gmail, Outlook, or any SMTP provider via .env config.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_html(customer_name: str, amount: float, short_url: str, invoice_id: str) -> str:
    """Build a clean HTML email body for the payment link."""
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f4f4;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
        <tr>
          <td align="center">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:8px;overflow:hidden;
                          box-shadow:0 2px 8px rgba(0,0,0,0.08);">

              <!-- Header -->
              <tr>
                <td style="background:#2563eb;padding:32px 40px;text-align:center;">
                  <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;">
                    Payment Due — Revenue Recovery
                  </h1>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:36px 40px;">
                  <p style="margin:0 0 16px;font-size:16px;color:#374151;">
                    Dear <strong>{customer_name}</strong>,
                  </p>
                  <p style="margin:0 0 24px;font-size:15px;color:#6b7280;line-height:1.6;">
                    As discussed, your payment of
                    <strong style="color:#111827;">₹{amount:,.2f}</strong>
                    for invoice <strong style="color:#111827;">{invoice_id}</strong>
                    is pending. Please use the button below to complete your payment securely.
                  </p>

                  <!-- CTA Button -->
                  <table cellpadding="0" cellspacing="0" style="margin:0 auto 32px;">
                    <tr>
                      <td align="center" style="border-radius:6px;background:#2563eb;">
                        <a href="{short_url}"
                           style="display:inline-block;padding:14px 36px;
                                  color:#ffffff;font-size:16px;font-weight:600;
                                  text-decoration:none;border-radius:6px;">
                          Pay Now — ₹{amount:,.2f}
                        </a>
                      </td>
                    </tr>
                  </table>

                  <p style="margin:0 0 8px;font-size:13px;color:#9ca3af;">
                    Or copy this link into your browser:
                  </p>
                  <p style="margin:0 0 24px;font-size:13px;word-break:break-all;">
                    <a href="{short_url}" style="color:#2563eb;">{short_url}</a>
                  </p>

                  <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 24px;">

                  <p style="margin:0;font-size:13px;color:#9ca3af;line-height:1.6;">
                    This is an automated message from the AI Revenue Recovery system.
                    If you have already made this payment, please ignore this email.
                  </p>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="background:#f9fafb;padding:20px 40px;text-align:center;">
                  <p style="margin:0;font-size:12px;color:#9ca3af;">
                    © 2025 Revenue Recovery · Powered by Razorpay
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


async def send_payment_link_email(
    to_email: str,
    customer_name: str,
    amount: float,
    short_url: str,
    invoice_id: str,
) -> bool:
    """
    Send the Razorpay payment link to the customer via SMTP.
    Returns True on success, False on failure (non-blocking).
    Requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in .env.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("⚠️  SMTP credentials not configured — skipping email notification")
        return False

    subject = f"Payment Due: ₹{amount:,.2f} for Invoice {invoice_id}"
    html_body = _build_html(customer_name, amount, short_url, invoice_id)
    plain_body = (
        f"Dear {customer_name},\n\n"
        f"Your payment of ₹{amount:,.2f} for invoice {invoice_id} is pending.\n"
        f"Please pay here: {short_url}\n\n"
        f"If you have already paid, please ignore this email."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Revenue Recovery <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())

        logger.info(f"✅ Payment link email sent to {to_email} for invoice {invoice_id}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ SMTP authentication failed — check SMTP_USER and SMTP_PASSWORD in .env")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP error sending email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending email to {to_email}: {e}")
        return False
