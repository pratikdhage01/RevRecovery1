"""
Email service for sending payment link notifications to customers.
Uses SMTP (Gmail App Password by default) configured via environment variables.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_payment_email(
    customer_name: str,
    invoice_id: str,
    amount: float,
    payment_link: str,
) -> tuple:
    """Build a payment link email (plain-text + HTML multipart)."""
    subject = f"Payment Link for Invoice {invoice_id} - Rs.{amount:,.0f} Due"

    plain = f"""Dear {customer_name},

Please find your payment link below to clear the outstanding amount for invoice {invoice_id}.

  Amount Due : Rs.{amount:,.2f}
  Pay Now    : {payment_link}

This link was generated securely via Razorpay. If you have already paid, please ignore this email.

Thank you,
Revenue Recovery Team
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 560px; margin: 40px auto; background: #ffffff;
                border-radius: 8px; overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .header {{ background: #0f172a; padding: 28px 32px; }}
    .header h1 {{ color: #ffffff; font-size: 20px; margin: 0; }}
    .body {{ padding: 32px; color: #374151; }}
    .amount-box {{ background: #f0fdf4; border: 1px solid #bbf7d0;
                   border-radius: 6px; padding: 16px 20px; margin: 24px 0; }}
    .amount-box .label {{ font-size: 13px; color: #6b7280; margin-bottom: 4px; }}
    .amount-box .value {{ font-size: 28px; font-weight: 700; color: #111827; }}
    .btn {{ display: inline-block; background: #2563eb; color: #ffffff !important;
             text-decoration: none; padding: 14px 28px; border-radius: 6px;
             font-size: 15px; font-weight: 600; margin-top: 8px; }}
    .footer {{ background: #f9fafb; padding: 20px 32px; font-size: 12px;
               color: #9ca3af; border-top: 1px solid #e5e7eb; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>Payment Request</h1>
    </div>
    <div class="body">
      <p>Dear <strong>{customer_name}</strong>,</p>
      <p>A payment link has been generated for your outstanding invoice
         <strong>{invoice_id}</strong>.</p>
      <div class="amount-box">
        <div class="label">Amount Due</div>
        <div class="value">Rs.{amount:,.2f}</div>
      </div>
      <a class="btn" href="{payment_link}">Pay Now</a>
      <p style="margin-top:24px; font-size:13px; color:#6b7280;">
        If you have already made the payment, please disregard this email.
        The link was generated securely via Razorpay.
      </p>
    </div>
    <div class="footer">
      Revenue Recovery Team - This is an automated notification.
    </div>
  </div>
</body>
</html>"""

    return subject, plain, html


async def send_payment_link_email(
    to_email: str,
    customer_name: str,
    invoice_id: str,
    amount: float,
    payment_link: str,
) -> bool:
    """
    Send a payment link email to the customer.

    Returns True on success, False on failure (logs the error).
    Skips silently if SMTP_USER is not configured.
    """
    if not settings.SMTP_USER:
        logger.warning("SMTP_USER not configured — skipping payment link email.")
        return False

    subject, plain, html = _build_payment_email(
        customer_name=customer_name,
        invoice_id=invoice_id,
        amount=amount,
        payment_link=payment_link,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(str(settings.SMTP_USER), str(settings.SMTP_PASSWORD))
            server.sendmail(str(settings.SMTP_USER), to_email, msg.as_string())

        logger.info(
            f"Email sent: payment link to {to_email} "
            f"(invoice={invoice_id}, amount=Rs.{amount:,.0f})"
        )
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. "
            "Check SMTP_USER / SMTP_PASSWORD (use a Gmail App Password)."
        )
    except smtplib.SMTPException as exc:
        logger.error(f"SMTP error while sending email to {to_email}: {exc}")
    except OSError as exc:
        logger.error(f"Network error while connecting to SMTP server: {exc}")

    return False


async def send_reminder_email(
    to_email: str,
    customer_name: str,
    invoice_id: str,
    amount: float,
    payment_link: Optional[str] = None,
) -> bool:
    """
    Send a gentle payment reminder email.
    If a payment_link is provided the button is included; otherwise it is omitted.
    """
    if not settings.SMTP_USER:
        logger.warning("SMTP_USER not configured — skipping reminder email.")
        return False

    subject = f"Reminder: Outstanding Payment for Invoice {invoice_id}"

    link_section_plain = f"\n  Pay Now : {payment_link}\n" if payment_link else ""
    link_section_html = (
        f'<a class="btn" href="{payment_link}">Pay Now</a>'
        if payment_link
        else ""
    )

    plain = f"""Dear {customer_name},

This is a friendly reminder that your payment of Rs.{amount:,.2f} for invoice {invoice_id} is still outstanding.
{link_section_plain}
Please clear the dues at your earliest convenience to avoid any service disruption.

Thank you,
Revenue Recovery Team
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 560px; margin: 40px auto; background: #ffffff;
                border-radius: 8px; overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .header {{ background: #0f172a; padding: 28px 32px; }}
    .header h1 {{ color: #ffffff; font-size: 20px; margin: 0; }}
    .body {{ padding: 32px; color: #374151; }}
    .amount-box {{ background: #fff7ed; border: 1px solid #fed7aa;
                   border-radius: 6px; padding: 16px 20px; margin: 24px 0; }}
    .amount-box .label {{ font-size: 13px; color: #6b7280; margin-bottom: 4px; }}
    .amount-box .value {{ font-size: 28px; font-weight: 700; color: #111827; }}
    .btn {{ display: inline-block; background: #2563eb; color: #ffffff !important;
             text-decoration: none; padding: 14px 28px; border-radius: 6px;
             font-size: 15px; font-weight: 600; margin-top: 8px; }}
    .footer {{ background: #f9fafb; padding: 20px 32px; font-size: 12px;
               color: #9ca3af; border-top: 1px solid #e5e7eb; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>Payment Reminder</h1>
    </div>
    <div class="body">
      <p>Dear <strong>{customer_name}</strong>,</p>
      <p>This is a friendly reminder that your payment for invoice
         <strong>{invoice_id}</strong> is still outstanding.</p>
      <div class="amount-box">
        <div class="label">Amount Due</div>
        <div class="value">Rs.{amount:,.2f}</div>
      </div>
      {link_section_html}
      <p style="margin-top:24px; font-size:13px; color:#6b7280;">
        Please clear the dues at your earliest convenience to avoid
        any service disruption.
      </p>
    </div>
    <div class="footer">
      Revenue Recovery Team - This is an automated notification.
    </div>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(str(settings.SMTP_USER), str(settings.SMTP_PASSWORD))
            server.sendmail(str(settings.SMTP_USER), to_email, msg.as_string())

        logger.info(
            f"Email sent: reminder to {to_email} "
            f"(invoice={invoice_id}, amount=Rs.{amount:,.0f})"
        )
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. "
            "Check SMTP_USER / SMTP_PASSWORD (use a Gmail App Password)."
        )
    except smtplib.SMTPException as exc:
        logger.error(f"SMTP error while sending reminder to {to_email}: {exc}")
    except OSError as exc:
        logger.error(f"Network error while connecting to SMTP server: {exc}")

    return False
