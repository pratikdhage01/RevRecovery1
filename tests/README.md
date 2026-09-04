# 🧪 AI Revenue Recovery — Test Scenarios & Verification Guide

This guide contains the complete verification suite for the **AI Revenue Recovery Agent**, covering both **deterministic automated unit tests** and **10 interactive voice demo scenarios**.

---

## 📋 Table of Contents

- [Automated Policy Engine Tests](#-automated-policy-engine-tests)
- [Voice Agent Demo Scenarios](#-voice-agent-demo-scenarios)
  - [Scenario 1: Successful Recovery (CUS_001)](#scenario-1--successful-recovery-rahul-sharma-cus_001)
  - [Scenario 2: Promise to Pay (CUS_002)](#scenario-2--promise-to-pay-priya-mehta-cus_002)
  - [Scenario 3: Invoice Dispute (CUS_003)](#scenario-3--invoice-dispute-amit-enterprises-cus_003)
  - [Scenario 4: Already Paid (CUS_004)](#scenario-4--already-paid-neha-joshi-cus_004)
  - [Scenario 5: High-Value Escalation (CUS_005)](#scenario-5--high-value-transaction-arjun-kapoor-cus_005)
  - [Scenario 6: Contact Change Attempt](#scenario-6--contact-change-attempt-security-block)
  - [Scenario 7: Unknown Customer](#scenario-7--unknown-customer)
  - [Scenario 8: Amount Mismatch](#scenario-8--amount-mismatch)
  - [Scenario 9: Customer Refusal](#scenario-9--customer-refuses-to-pay)
  - [Scenario 10: Query Failure Reason](#scenario-10--why-did-payment-fail)
- [Database Reset for Testing](#-database-reset-for-clean-testing)

---

## ⚡ Automated Policy Engine Tests

The deterministic policy engine has 100% rule-level automated unit test coverage across 25 distinct scenarios.

### Running the Test Suite

```bash
# Navigate to backend directory
cd backend

# Run pytest with verbose output
pytest tests/test_policy_engine.py -v
```

### Test Coverage Summary

| Rule Tested | Condition | Expected Decision |
|---|---|---|
| Rule 1 | `payment_status == PAID` | `STOP_PAID` |
| Rule 2 | `amount_due <= 0` | `STOP_NO_DUE` |
| Rule 3 | Unknown / unverified customer | `ESCALATE` |
| Rule 4 | Contact change requested (`request_contact_change=True`) | `ESCALATE` |
| Rule 5 | Invoice dispute raised (`dispute_raised=True`) | `ESCALATE` |
| Rule 6 | Customer refuses to pay (`customer_refuses=True`) | `STOP_REFUSED` |
| Rule 7 | Amount mismatch between customer and database | `CLARIFY` |
| Rule 8 | `call_attempts >= MAX_CALL_ATTEMPTS` (default: 2) | `STOP_MAX_ATTEMPTS` |
| Rule 9 | `recovery_days > MAX_RECOVERY_DAYS` (default: 7) | `STOP_WINDOW_EXPIRED` |
| Rule 10 | Customer makes Promise to Pay (`promise_to_pay=True`) | `TRACK_PROMISE_TO_PAY` |
| Rule 11a | Verified + willing + active link exists | `RESEND_EXISTING_LINK` |
| Rule 11b | Verified + willing + amount > ₹25,000 | `ESCALATE` |
| Rule 11c | Verified + willing + amount between ₹5,001 and ₹25,000 | `NEEDS_ADDITIONAL_VERIFICATION` |
| Rule 11d | Verified + willing + amount ≤ ₹5,000 | `RECOVER_NOW` |

---

## 🎙️ Voice Agent Demo Scenarios

Use these scripts while testing or demoing the voice agent from the frontend customer page (`/customers/[id]`).

### Scenario 1 — Successful Recovery (Rahul Sharma, CUS_001)

* **Context:** Invoice `INV_001` overdue ₹2,499. Payment method failed (Card Declined).
* **Target Policy:** `RECOVER_NOW`

```text
AI:
Namaste Rahul, main AI Revenue Recovery team se bol raha hoon.
Aapke account par ₹2,499 ka payment pending hai invoice INV_001 ke liye.
Kya aap iske baare mein baat karna chahenge?

You (as customer):
Haan, payment karna hai but card se nahi ho raha.

AI:
Samajh gaya. Aapki card payment fail ho gayi hai. Kya aap alternative
payment method se payment complete karna chahenge? Jaise UPI ya netbanking?

You:
Haan, main UPI se kar sakta hoon.

AI:
Bilkul. Main check karta hoon... [Policy evaluated: RECOVER_NOW]
Aapka verification complete ho gaya hai aur amount ₹2,499 confirm hai.
Main aapke registered contact par secure Razorpay payment link bhej raha hoon.
```

**System Behavior:**
1. LLM extracts signals: `customer_verified=True`, `willing_to_pay=True`, `stated_amount=2499`.
2. Policy Engine validates: Amount ≤ ₹5,000, no disputes, attempts < 2 → `RECOVER_NOW`.
3. Backend creates Razorpay Payment Link for ₹2,499.
4. When paid in test mode, Razorpay Webhook updates DB → Dashboard reflects recovered revenue.

---

### Scenario 2 — Promise to Pay (Priya Mehta, CUS_002)

* **Context:** Overdue ₹4,999.
* **Target Policy:** `TRACK_PROMISE_TO_PAY`

```text
AI:
Namaste Priya, main AI Revenue Recovery team se bol raha hoon.
Aapke account par ₹4,999 ka payment 5 din se overdue hai.
Kya aap iske baare mein baat karna chahenge?

You:
Haan, but abhi payment nahi kar sakti. Kal salary aayegi, kal payment kar dungi.

AI:
Samajh aaya. Koi problem nahi. Kya aap kal payment kar sakti hain?

You:
Haan, kal pakka.

AI:
Theek hai. Main aapka promise-to-pay record kar raha hoon kal ke liye.
Koi pressure nahi. Agar koi help chahiye toh hum contact karenge.
```

**System Behavior:**
1. Date extracted by LLM: Next day.
2. Policy: `TRACK_PROMISE_TO_PAY`.
3. PTP recorded in MongoDB audit log. **Zero payment links generated**.

---

### Scenario 3 — Invoice Dispute (Amit Enterprises, CUS_003)

* **Context:** Overdue ₹18,500.
* **Target Policy:** `ESCALATE`

```text
AI:
Namaste, main Amit Enterprises ke liye AI Revenue Recovery team se hoon.
₹18,500 ka invoice INV_003 overdue hai.

You:
Ye invoice galat hai. Humne ye service approve hi nahi ki thi. Ye amount galat hai.

AI:
Samajh gaya. Aap invoice dispute kar rahe hain. Main ye case hamare
human review team ke paas escalate kar raha hoon.
Koi automated payment link generate nahi hoga. Aapko ek confirmation email aayega.
```

**System Behavior:**
1. Signal `dispute_raised=True` captured.
2. Rule 5 triggers `ESCALATE`.
3. Audit recorded: `DISPUTE_DETECTED` and `ESCALATED_TO_HUMAN`. No link generated.

---

### Scenario 4 — Already Paid (Neha Joshi, CUS_004)

* **Context:** `payment_status == PAID` in MongoDB.
* **Target Policy:** `STOP_PAID`

```text
AI:
Namaste Neha, main AI Revenue Recovery team se hoon.
[checks database]

System immediately triggers Rule 1:
→ Policy: STOP_PAID
→ AI: "Aapka payment pehle se complete hai. Koi action required nahi. Thank you!"
```

**System Behavior:**
1. Stopped immediately before generating any collection request.

---

### Scenario 5 — High-Value Transaction (Arjun Kapoor, CUS_005)

* **Context:** Amount pending ₹75,000 (> threshold ₹25,000).
* **Target Policy:** `ESCALATE`

```text
AI:
Namaste Arjun, main AI Revenue Recovery team se hoon.
Aapke account par ₹75,000 ka payment pending hai.

You:
Haan main payment karna chahta hoon, mera payment method fail hua tha.

AI:
Samajh gaya. Lekin ₹75,000 ek high-value transaction hai.
Iske liye humara senior team verify karega aur aapse contact karega.
Automated recovery is amount ke liye allowed nahi hai.
```

**System Behavior:**
1. Amount > `HIGH_VALUE_THRESHOLD` (₹25,000).
2. Rule 11b blocks automated link creation and forces `ESCALATE`.

---

### Scenario 6 — Contact Change Attempt (Security Block)

* **Target Policy:** `ESCALATE`

```text
You:
Payment link mere naye number pe bhej do — 9999988888.

AI:
Maafi chahta hoon, lekin registered contact details change karna
is call mein possible nahi hai security reasons se.
Ye case hamare team ke paas escalate kar raha hoon.
```

**System Behavior:**
1. Signal `request_contact_change=True`.
2. Rule 4 triggers immediate `ESCALATE` to prevent account takeover or link redirection attacks.
3. Audit logged: `CONTACT_CHANGE_BLOCKED`.

---

### Scenario 7 — Unknown Customer

* **Target Policy:** `ESCALATE`

```text
You:
Mera ₹5,000 ka payment pending hai.

System:
→ Customer not found in database / ID unverified
→ Policy: ESCALATE
→ Prevents generating unauthorized invoices or payment links
```

---

### Scenario 8 — Amount Mismatch

* **Context:** DB records ₹2,499; Customer claims ₹4,999.
* **Target Policy:** `CLARIFY`

```text
Database: ₹2,499
You: Mera ₹4,999 ka payment pending hai.

AI:
Humara record ₹2,499 dikhata hai aapke invoice ke liye.
₹4,999 match nahi kar raha. Kya aap invoice number confirm kar sakte hain?
```

**System Behavior:**
1. Stated amount != DB amount.
2. Policy: `CLARIFY`. Automated link creation strictly blocked until reconciliation.

---

### Scenario 9 — Customer Refuses to Pay

* **Target Policy:** `STOP_REFUSED`

```text
You:
Mujhe payment nahi karna. Main nahi karunga.

AI:
Theek hai, koi pressure nahi hai. Main aapki baat samajhta hoon.
Aapka refusal record kar raha hoon. Agar kabhi zaroorat ho toh hume contact karen.
```

**System Behavior:**
1. Signal `customer_refuses=True`.
2. Rule 6 triggers `STOP_REFUSED`.
3. Audit log records refusal; ceases outbound harassment.

---

### Scenario 10 — Why Did Payment Fail?

* **Target Policy:** Accurate context retrieval from MongoDB

```text
You:
Kyun payment fail hua mera?

AI:
[fetches failure_reason from MongoDB: CARD_DECLINED]
Aapki card payment decline hui thi. Bank ki taraf se decline aaya tha.
Aap alternative method (jaise UPI ya Netbanking) try kar sakte hain.
```

**System Behavior:**
1. Agent answers using real DB ground truth (`failure_reason`).
2. Zero hallucinations on payment failure specifics.

---

## 🔄 Database Reset for Clean Testing

To reset all customer states, clear test audit trails, and re-seed the fresh demo dataset:

```bash
cd backend
python scripts/reset_db.py
```
