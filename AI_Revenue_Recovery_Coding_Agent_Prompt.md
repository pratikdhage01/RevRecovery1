# CODING AGENT PROMPT — AI REVENUE RECOVERY AGENT

You are a senior full-stack engineer and AI agent architect.

The problem statement is:

> **AI Revenue Recovery**  
> Find revenue that's slipping away and win it back.
>
> Build an agent that detects revenue at risk, determines the right intervention, and executes a bounded recovery workflow: from payment failures and checkout abandonment to overdue receivables.
>
> The solution should demonstrate measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail.

Use the attached Track 03 screenshot as the primary reference for the problem statement.

I want to build an **AI Revenue Recovery Agent with a Hinglish voice interface using LiveKit**.

The goal is NOT to build merely a voice chatbot.

The goal is to build an **agentic revenue recovery system** where:

```text
Revenue at Risk
      ↓
Detect / Analyze Problem
      ↓
Understand Customer
      ↓
Verify Customer + Payment Context
      ↓
Determine Root Cause
      ↓
Policy Engine
      ↓
Choose Appropriate Recovery Action
      ↓
Hinglish Voice Conversation
      ↓
Execute Action
      ↓
Razorpay Test Mode Payment Link
      ↓
Customer Pays
      ↓
Razorpay Webhook
      ↓
Confirm Revenue Recovered
      ↓
Audit Trail + Dashboard
```

Use [LiveKit](https://livekit.com/) for the realtime voice agent.

---

# 1. HIGH-LEVEL PRODUCT

Build a working prototype called:

**AI Revenue Recovery Agent**

The system should allow a business to see customers whose revenue is at risk and start a voice-based recovery conversation.

The voice agent should:

- Speak naturally in Hinglish.
- Understand English, Hindi, and mixed Hinglish.
- Understand the customer's problem.
- Retrieve the customer's payment context from MongoDB.
- Verify the customer against known information.
- Identify the payment/revenue issue.
- Determine customer intent.
- Apply deterministic recovery policies.
- Decide whether it can recover automatically, needs clarification, should track a promise-to-pay, or must escalate.
- If recovery is permitted, create a Razorpay **Test Mode Payment Link**.
- Send/provide the payment link through the appropriate registered contact.
- Track payment status.
- React to Razorpay webhook events.
- Mark the recovered amount when payment succeeds.
- Maintain a complete audit trail.

The agent must **NOT** blindly create payment links based solely on what the customer says.

---

# 2. VERY IMPORTANT ARCHITECTURAL PRINCIPLE

Separate:

### LLM reasoning

from:

### Deterministic Policy Engine

The LLM can:

- Understand natural language.
- Extract intent.
- Extract entities.
- Understand Hinglish.
- Identify customer concerns.
- Extract promise-to-pay dates.
- Recommend a possible action.

But the LLM must **NOT have unrestricted authority** to create payment links.

The final decision must go through a deterministic backend policy engine.

Architecture:

```text
                    LIVEKIT VOICE AGENT
                           │
                           ▼
                  Conversation / LLM
                           │
                           ▼
                   Structured Context
                           │
                           ▼
                  DETERMINISTIC POLICY
                       ENGINE
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          RECOVER       CLARIFY       ESCALATE
             │
             ▼
      Razorpay Payment Link
```

This separation is a core feature of the project.

---

# 3. PROJECT STRUCTURE

Create **separate frontend and backend folders**.

The final repository should approximately look like:

```text
ai-revenue-recovery/
│
├── frontend/
│   ├── ...
│   ├── package.json
│   └── README.md
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── models/
│   │   ├── services/
│   │   ├── policies/
│   │   ├── webhooks/
│   │   ├── database/
│   │   └── main.py
│   │
│   ├── scripts/
│   │   └── seed_customers.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── README.md
├── .gitignore
└── ...
```

Do NOT mix frontend and backend code.

---

# 4. FRONTEND

Use a modern frontend stack such as:

- Next.js
- React
- TypeScript
- Tailwind CSS

The frontend should primarily be a **Revenue Recovery Dashboard**.

It should NOT be a generic landing page.

The main screen should communicate:

> "This company has revenue at risk, and the AI agent is recovering it."

---

# 5. DASHBOARD REQUIREMENTS

Create an attractive, professional SaaS/fintech-style dashboard.

Include top-level metrics such as:

```text
Revenue At Risk
₹4,82,500

Revenue Recovered
₹1,37,400

Recovery Rate
28.4%

Active Recoveries
7

Customers Contacted
51
```

These should ideally come from backend APIs rather than hardcoded values.

## Customer / Recovery table

Display customers with information such as:

```text
Customer
Amount Due
Issue
Risk
Days Overdue
Recovery Status
Last Action
```

Example:

```text
Rahul Sharma
₹2,499
Card Declined
High
1 day
Calling
Attempt 1/2
```

Clicking a customer should show a detailed recovery view.

---

# 6. CUSTOMER RECOVERY DETAIL VIEW

For each customer, show:

```text
Customer Information

Name
Phone
Email

Payment Information

Invoice ID
Amount Due
Payment Status
Failure Reason
Days Overdue
Previous Attempts

Recovery Information

Recovery Score
Customer Intent
Verification Status
Current Recovery Decision
Number of Calls
Payment Links Generated
Promise-to-Pay
Next Action
```

Also display an **AI Decision Explanation**.

Example:

```text
AI RECOVERY DECISION

Customer: Rahul Sharma
Amount: ₹2,499

Root Cause:
Card payment declined

Customer Intent:
Willing to pay

Verification:
✓ Customer matched
✓ Invoice matched
✓ Amount confirmed
✓ No dispute

Policy Checks:
✓ Amount within auto-recovery limit
✓ Recovery window active
✓ Call attempts below maximum
✓ No active payment link

Decision:
CREATE PAYMENT LINK

Reason:
Customer is verified, willing to pay,
and the original payment method failed.
```

---

# 7. LIVEKIT VOICE AGENT UI

The frontend must contain a prominent button:

### "Start AI Recovery Call"

When clicked:

```text
Browser
   ↓
Request microphone permission
   ↓
Connect to LiveKit room
   ↓
Start voice agent
```

The user should be able to speak directly through the browser microphone.

Do NOT require a phone number or external telephony for the first version.

This is intentionally **Option A: browser microphone + LiveKit**.

Use the official LiveKit client/agent architecture.

The UI should show:

```text
● AI Agent Connected

Listening...

[ Microphone animation ]

AI Revenue Recovery Agent
```

Also show:

- Connection status
- Microphone status
- Current customer
- Current recovery stage
- AI decision
- Payment link status
- Recovery status

---

# 8. VOICE AGENT BEHAVIOR

The voice agent should sound like a professional Indian customer-support/payment-recovery representative.

It should naturally use Hinglish.

Example:

> "Namaste Rahul, main AI Revenue Recovery team se bol raha hoon. Aapke account par ₹2,499 ka payment pending hai kyunki previous payment attempt complete nahi hua tha. Kya aap isi payment ke baare mein baat karna chahenge?"

Do NOT make the agent overly robotic.

It should:

- Listen carefully.
- Ask one question at a time.
- Not repeatedly interrupt.
- Understand Hinglish.
- Understand Hindi.
- Understand English.
- Keep the conversation concise.
- Never pressure the customer aggressively.
- Never invent payment information.
- Never invent invoice information.
- Never claim that payment succeeded unless backend/webhook confirms it.

---

# 9. CUSTOMER CONTEXT

The agent should have backend tools/functions such as:

```text
get_customer()
get_invoice()
get_payment_status()
get_payment_history()
get_existing_payment_links()
get_recovery_history()
```

The agent should retrieve information from MongoDB.

The customer should NOT be able to override database information simply by saying something different.

For example:

Database:

```text
amount_due = ₹2,499
```

Customer:

> "Mera ₹4,999 ka payment hai."

The agent should recognize the mismatch and NOT create a ₹4,999 link.

Instead:

```text
CLARIFY / ESCALATE
```

---

# 10. POLICY ENGINE

Implement a dedicated policy engine.

For example:

```text
backend/app/policies/recovery_policy.py
```

The policy engine should return structured decisions.

Possible decisions:

```text
RECOVER_NOW
RESEND_EXISTING_LINK
ALTERNATIVE_RECOVERY
CLARIFY
TRACK_PROMISE_TO_PAY
ESCALATE
STOP_PAID
STOP_NO_DUE
STOP_MAX_ATTEMPTS
STOP_WINDOW_EXPIRED
```

---

# 11. POLICY RULES

Implement deterministic rules.

## Rule 1 — Already Paid

If:

```text
payment_status == PAID
```

Then:

```text
STOP_PAID
```

Never create another payment link.

---

## Rule 2 — Nothing Due

If:

```text
amount_due <= 0
```

Then:

```text
STOP_NO_DUE
```

---

## Rule 3 — Invoice Dispute

If customer says:

- "I didn't make this purchase."
- "Invoice is wrong."
- "Amount is incorrect."
- "I already cancelled this."
- "I don't owe this money."

Then:

```text
ESCALATE
```

Do NOT attempt automated recovery.

---

## Rule 4 — Identity / Context Mismatch

If the customer cannot sufficiently confirm the transaction context:

```text
ESCALATE
```

Do not let the LLM decide that the customer is legitimate based purely on conversational behavior.

Verification should be based on backend/customer context.

---

## Rule 5 — Customer Wants to Pay

If:

```text
customer_verified == true
AND
customer_willing_to_pay == true
AND
no_dispute == true
AND
amount_due > 0
```

then evaluate whether automated recovery is allowed.

---

## Rule 6 — Existing Payment Link

If an active payment link already exists:

```text
RESEND_EXISTING_LINK
```

Do not unnecessarily create duplicate payment links.

---

## Rule 7 — High Value Transaction

For the prototype, use configurable thresholds.

Example:

```text
₹0 – ₹5,000
→ automatic recovery

₹5,001 – ₹25,000
→ additional verification

> ₹25,000
→ human escalation
```

Make these values configurable through environment/configuration rather than hardcoded everywhere.

These are demo/business policies and should NOT be presented as Razorpay requirements.

---

# 12. PAYMENT FAILURE POLICIES

Support different failure scenarios.

Example:

### Card Declined

```text
CARD_DECLINED
       ↓
Ask customer whether they want an alternative payment method
       ↓
Customer agrees
       ↓
Create Razorpay Payment Link
```

### Checkout Abandoned

```text
CHECKOUT_ABANDONED
       ↓
Ask why checkout wasn't completed
       ↓
If customer wants to complete payment
       ↓
Generate payment link
```

### Failed Subscription

```text
SUBSCRIPTION_PAYMENT_FAILED
       ↓
Explain payment issue
       ↓
Customer willing to pay
       ↓
Generate payment link
```

### Overdue B2B Invoice

If amount is high or customer disputes it:

```text
ESCALATE
```

If customer confirms the invoice and promises payment later:

```text
TRACK_PROMISE_TO_PAY
```

---

# 13. PROMISE-TO-PAY

This is an important feature.

If customer says something like:

> "Bhai kal salary aayegi, kal payment kar dunga."

The LLM should extract:

```json
{
  "promise_to_pay": true,
  "promised_date": "YYYY-MM-DD",
  "amount": 2499
}
```

Store this in MongoDB.

Do NOT immediately generate another payment link unless policy says it is appropriate.

The dashboard should display:

```text
Promise to Pay

Amount: ₹2,499
Promised Date: 4 Sep 2026
Status: Pending
```

---

# 14. CONTACT CHANGE SAFETY

If the customer says:

> "Payment link mere naye number par bhej do."

Do NOT automatically change the registered contact.

For the prototype:

```text
CONTACT_CHANGE_REQUESTED
        ↓
ESCALATE
```

The payment link should normally be sent to the verified/registered contact stored in the database.

---

# 15. ATTEMPT LIMITS / BOUNDED AUTONOMY

The workflow MUST be bounded.

Create configurable limits such as:

```text
MAX_CALL_ATTEMPTS = 2
MAX_PAYMENT_LINKS = 2
MAX_REMINDERS = 2
MAX_RECOVERY_DAYS = 7
```

If limits are exceeded:

```text
STOP / ESCALATE
```

The dashboard should clearly show:

```text
Recovery Policy

Call Attempts       1 / 2
Payment Links       1 / 2
Reminders           0 / 2
Recovery Window     Day 1 / 7
```

---

# 16. RAZORPAY INTEGRATION

Use **Razorpay Test Mode only**.

Do NOT use production payment credentials.

Use Razorpay Payment Links API.

Create backend services such as:

```text
create_payment_link()
get_payment_link()
cancel_payment_link()
check_payment_status()
```

The agent should call backend tools, and the backend should communicate with Razorpay.

Architecture:

```text
LiveKit Agent
     ↓
Agent Tool
     ↓
FastAPI Backend
     ↓
Razorpay API
     ↓
Payment Link
```

Do NOT put Razorpay secret keys in frontend code.

Use:

```text
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
```

in backend environment variables.

Use:

```text
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
MONGODB_URI
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
LLM/API keys
```

in `.env`.

Provide a complete `.env.example`.

---

# 17. RAZORPAY WEBHOOK

Implement a Razorpay webhook endpoint.

For example:

```text
POST /api/webhooks/razorpay
```

Use webhook events to determine whether payment actually succeeded.

The webhook should:

1. Verify webhook signature.
2. Identify the relevant payment link/invoice/customer.
3. Update MongoDB.
4. Mark revenue as recovered.
5. Create an audit event.
6. Update the dashboard.

Never mark a customer as "Paid" merely because the AI generated a payment link.

The actual source of truth for successful payment should be the Razorpay payment event/webhook.

---

# 18. RECOVERY LEDGER / AUDIT TRAIL

Create an audit collection in MongoDB.

Every important action should create an event.

Example:

```json
{
  "customer_id": "CUS_001",
  "invoice_id": "INV_001",
  "event": "PAYMENT_LINK_CREATED",
  "amount": 2499,
  "actor": "AI_AGENT",
  "reason": "Verified customer willing to pay",
  "timestamp": "..."
}
```

Other events:

```text
RECOVERY_STARTED
CUSTOMER_VERIFIED
PAYMENT_CONTEXT_RETRIEVED
ROOT_CAUSE_IDENTIFIED
POLICY_EVALUATED
PAYMENT_LINK_CREATED
PAYMENT_LINK_SENT
PROMISE_TO_PAY_RECORDED
PAYMENT_RECEIVED
REVENUE_RECOVERED
RECOVERY_STOPPED
ESCALATED_TO_HUMAN
```

The dashboard should have an **Audit Trail** section.

---

# 19. RECOVERY SCORE

Implement a recovery score for prioritization/explanation.

Example:

```text
Customer Intent       30/30
Payment History       20/20
Verification          20/20
Amount Risk           15/15
Recovery Window       10/10
--------------------------------
Recovery Score        95/100
```

Make the scoring logic transparent and deterministic.

Do NOT allow the LLM to arbitrarily assign the final score.

Use the score mainly for:

- Prioritization
- Dashboard display
- Explanation

The hard policy rules should still override the score.

---

# 20. FIVE TEST CUSTOMERS IN MONGODB

Create a script:

```text
backend/scripts/seed_customers.py
```

It should insert **exactly 5 realistic test customers** into MongoDB.

Make the data intentionally cover different policy scenarios.

Use dummy/test contact information only.

Suggested dataset:

---

## Customer 1 — Successful recovery candidate

```text
Name: Rahul Sharma
Customer ID: CUS_001
Invoice: INV_001
Amount: ₹2,499
Status: PAYMENT_FAILED
Failure: CARD_DECLINED
Days overdue: 1
Previous attempts: 1
Dispute: false
Registered phone: dummy/test number
Registered email: dummy/test email
```

Expected behavior:

```text
Verified
+
Willing to pay
+
Low amount
+
Card failed

→ CREATE PAYMENT LINK
```

---

## Customer 2 — Promise to Pay

```text
Name: Priya Mehta
Customer ID: CUS_002
Invoice: INV_002
Amount: ₹4,999
Status: OVERDUE
Days overdue: 5
Previous attempts: 1
Dispute: false
```

Expected conversation:

> "Abhi payment possible nahi hai, salary kal aayegi."

Expected:

```text
TRACK_PROMISE_TO_PAY
```

---

## Customer 3 — Invoice Dispute

```text
Name: Amit Enterprises
Customer ID: CUS_003
Invoice: INV_003
Amount: ₹18,500
Status: OVERDUE
Days overdue: 17
Dispute: false initially
```

During conversation the customer says:

> "Ye invoice galat hai, humne ye service approve nahi ki thi."

Expected:

```text
ESCALATE
```

No payment link should be generated.

---

## Customer 4 — Already Paid

```text
Name: Neha Joshi
Customer ID: CUS_004
Invoice: INV_004
Amount: ₹1,999
Status: PAID
```

Expected:

```text
STOP_PAID
```

No new payment link.

---

## Customer 5 — High Value / Verification

```text
Name: Arjun Kapoor
Customer ID: CUS_005
Invoice: INV_005
Amount: ₹75,000
Status: PAYMENT_FAILED
Failure: PAYMENT_METHOD_FAILED
Days overdue: 2
Dispute: false
```

Expected:

```text
HIGH VALUE
+
AUTOMATED RECOVERY NOT ALLOWED

→ ESCALATE
```

The exact names/contact data can be dummy data, but make the scenarios realistic.

---

# 21. ALSO CREATE TEST CUSTOMERS / EDGE CASE DATA IF USEFUL

If additional seed data is useful for automated tests, you may create separate fixtures, but the main seed script must clearly create the five primary demo customers above.

Make the seed script idempotent where possible.

For example:

```bash
python backend/scripts/seed_customers.py
```

should not create duplicate customers every time it is run.

---

# 22. TESTING THE POLICY ENGINE

Write automated tests for the policy engine.

At minimum test:

```text
Already paid
No amount due
Verified + willing to pay
Existing payment link
Card declined
Checkout abandoned
Promise to pay
Invoice dispute
Identity mismatch
High-value transaction
Maximum call attempts reached
Recovery window expired
Contact change requested
Customer refuses payment
Unknown intent
```

Tests should prove that the policy engine produces the expected decision.

---

# 23. DEMO VOICE CONVERSATIONS IN README

This is VERY IMPORTANT.

The README must contain a section:

# Demo Voice Conversations

Document realistic conversations that I can use while demoing the voice agent.

Include conversations for:

### Scenario 1 — Customer exists + payment failed + willing to pay

Example:

```text
AI:
Namaste Rahul, main AI Revenue Recovery team se bol raha hoon.
Aapke account par ₹2,499 ka payment pending hai.
Kya aap isi payment ke baare mein baat karna chahenge?

Customer:
Haan, payment karna hai but card se nahi ho raha.

AI:
Samajh gaya. Aap alternative payment method se payment complete karna chahenge?

Customer:
Haan.

AI:
Sure. Main aapke registered contact par secure payment link bhej raha hoon.
```

Expected:

```text
→ Customer verified
→ Root cause identified
→ Customer willing to pay
→ Policy PASS
→ Razorpay Payment Link created
→ Link sent
→ Payment webhook awaited
```

---

### Scenario 2 — Customer exists + Promise to Pay

Example:

```text
Customer:
Abhi payment nahi kar sakta, kal salary aayegi.
Kal payment kar dunga.

Expected:

→ Promise-to-pay extracted
→ Date extracted
→ No aggressive recovery
→ PTP stored
→ Follow-up scheduled
```

---

### Scenario 3 — Customer exists + invoice dispute

Example:

```text
Customer:
Ye invoice galat hai.
Maine ye service approve hi nahi ki.

Expected:

→ Dispute detected
→ Payment link NOT generated
→ Recovery stopped
→ Escalation created
```

---

### Scenario 4 — Customer exists + already paid

Expected:

```text
Customer:
Maine payment already kar diya hai.

System:
→ Check backend/Razorpay status

If paid:
→ STOP
→ Do not generate link
```

---

### Scenario 5 — High-value customer

Customer has ₹75,000 outstanding.

Expected:

```text
→ Additional verification
→ Automated payment link blocked
→ Human escalation
```

---

### Scenario 6 — Customer asks to send link to another number

Expected:

```text
Customer:
Mere doosre number pe link bhej do.

→ Do not change registered contact
→ Escalate
```

---

### Scenario 7 — Customer does NOT exist in database

This is VERY important.

Demonstrate:

```text
Unknown customer
     ↓
Customer says:
"Haan mera payment pending hai"
     ↓
System cannot find verified customer/invoice
     ↓
DO NOT create payment link
     ↓
Ask for safe verification/context
     ↓
If still unresolved
     ↓
ESCALATE
```

The AI must never invent a customer record.

---

### Scenario 8 — Customer gives incorrect amount

Database:

```text
₹2,499
```

Customer:

> "Mera ₹4,999 pending hai."

Expected:

```text
Mismatch detected
→ Clarify
→ Do NOT generate ₹4,999 link
```

---

### Scenario 9 — Customer refuses to pay

Example:

> "Mujhe payment nahi karna."

Expected:

```text
→ Respectfully end recovery
→ No repeated pressure
→ Record refusal
→ STOP
```

---

### Scenario 10 — Customer asks why payment failed

Agent should retrieve the known failure reason and explain it without inventing details.

---

# 24. README REQUIREMENTS

Create a comprehensive root `README.md`.

It should contain:

```text
1. Project Overview
2. Problem Statement
3. Why This Solves Track 03
4. Architecture
5. Tech Stack
6. Folder Structure
7. Environment Variables
8. MongoDB Setup
9. Seed Database
10. Backend Setup
11. Frontend Setup
12. LiveKit Setup
13. Razorpay Test Mode Setup
14. Razorpay Webhook Setup
15. Running the Application
16. Policy Engine
17. Recovery Decision Matrix
18. Demo Voice Conversations
19. Test Scenarios
20. Example Recovery Flow
21. Audit Trail
22. Future Improvements
```

Include architecture diagrams using Mermaid where useful.

---

# 25. RECOVERY DECISION MATRIX IN README

Include a table like:

| Situation | Decision |
|---|---|
| Already paid | STOP |
| No amount due | STOP |
| Verified + willing to pay | RECOVER |
| Existing active link | RESEND |
| Payment method failed | ALTERNATIVE RECOVERY |
| Promise to pay | TRACK PTP |
| Invoice dispute | ESCALATE |
| Identity mismatch | ESCALATE |
| High-value transaction | ESCALATE |
| Contact change | ESCALATE |
| Max attempts reached | STOP / ESCALATE |
| Recovery window expired | STOP |
| Unknown customer | ESCALATE |
| Customer refuses | STOP |

---

# 26. API DESIGN

Create clean backend APIs.

At minimum:

```text
GET  /api/customers
GET  /api/customers/:id
GET  /api/customers/:id/recovery
GET  /api/customers/:id/audit
GET  /api/dashboard/stats

POST /api/recovery/:customerId/start
POST /api/recovery/:customerId/evaluate
POST /api/recovery/:customerId/payment-link

POST /api/webhooks/razorpay

POST /api/livekit/token
```

Adapt naming to your chosen framework if necessary.

---

# 27. LIVEKIT TOKEN GENERATION

The backend should generate the LiveKit access token.

The frontend should never contain LiveKit API secrets.

Flow:

```text
Frontend
   ↓
POST /api/livekit/token
   ↓
Backend generates token
   ↓
Frontend receives token
   ↓
Frontend connects to LiveKit
   ↓
Voice Agent joins room
```

---

# 28. SECURITY

Follow basic security best practices.

Never expose:

```text
Razorpay Secret
LiveKit API Secret
LLM API Secret
MongoDB credentials
Webhook secret
```

to the frontend.

Use environment variables.

Validate API inputs.

Validate Razorpay webhook signatures.

Do not trust customer-provided amounts.

Do not allow the frontend to directly create arbitrary payment links.

All payment-link creation must pass through backend policy validation.

---

# 29. ERROR HANDLING

The system should gracefully handle:

```text
MongoDB unavailable
Razorpay API failure
Razorpay webhook failure
LiveKit connection failure
LLM failure
Voice agent disconnected
Payment link creation failure
Unknown customer
Missing customer contact
```

The UI should show meaningful errors rather than crashing.

---

# 30. DO NOT OVERENGINEER

This is a hackathon MVP.

Prioritize:

### MUST WORK

```text
MongoDB
   ↓
Customer
   ↓
LiveKit voice agent
   ↓
LLM understands conversation
   ↓
Policy engine
   ↓
Razorpay test Payment Link
   ↓
Webhook
   ↓
Revenue recovered
   ↓
Dashboard update
```

Do not spend excessive time building unnecessary microservices.

Keep the architecture clean and modular, but make the complete end-to-end flow work.

---

# 31. UI QUALITY

The frontend should look like a polished modern fintech SaaS product.

Use:

- Dark/light professional fintech aesthetic
- Clean typography
- Cards
- Tables
- Status badges
- Subtle animations
- Live activity indicators
- Recovery progress
- Voice waveform/microphone animation
- Clear success/error states
- Responsive design

The UI should make it immediately obvious:

> **How much revenue is at risk?**
>
> **How much has AI recovered?**
>
> **What is the AI doing right now?**
>
> **Why did the AI make that decision?**

Avoid making the dashboard unnecessarily flashy.

Prioritize clarity and credibility.

---

# 32. IMPORTANT PRODUCT PRINCIPLE

The project should communicate this architecture:

```text
LiveKit
= Voice / realtime interaction

LLM
= Natural language understanding + reasoning

Policy Engine
= Deterministic authority / bounded autonomy

MongoDB
= Customer + transaction + recovery state

Razorpay
= Payment execution

Razorpay Webhook
= Payment truth

Dashboard
= Monitoring + auditability
```

The LLM should NOT be the entire application.

---

# 33. FINAL DEMO FLOW

The application should support this demo:

```text
Open Dashboard
      ↓
See ₹X revenue at risk
      ↓
Select Rahul Sharma
      ↓
Click "Start AI Recovery Call"
      ↓
Browser asks for microphone
      ↓
LiveKit agent connects
      ↓
Agent speaks Hinglish
      ↓
Customer explains card problem
      ↓
Agent retrieves customer/payment context
      ↓
LLM extracts intent
      ↓
Policy Engine evaluates
      ↓
Decision = RECOVER_NOW
      ↓
Backend creates Razorpay Test Payment Link
      ↓
Agent tells customer link was sent
      ↓
Perform Razorpay test payment
      ↓
Webhook received
      ↓
MongoDB updated
      ↓
Dashboard updates
      ↓
Revenue Recovered += ₹2,499
      ↓
Audit Trail shows entire sequence
```

Then demonstrate a second customer:

```text
Customer disputes invoice
      ↓
Policy Engine
      ↓
ESCALATE
      ↓
NO payment link
```

Then demonstrate a third:

```text
Customer says:
"Kal payment karunga"
      ↓
Promise-to-Pay detected
      ↓
PTP recorded
```

This should clearly demonstrate that the system is **making different decisions depending on the situation**, rather than blindly sending payment links.

---

# 34. IMPLEMENTATION APPROACH

Before writing code:

1. Inspect the requirements above.
2. Design the architecture.
3. Create the folder structure.
4. Implement backend/database/models.
5. Implement deterministic policy engine.
6. Implement Razorpay integration.
7. Implement webhook.
8. Implement LiveKit voice agent.
9. Implement frontend dashboard.
10. Connect frontend to backend.
11. Add MongoDB seed script.
12. Add automated tests.
13. Add README and demo conversations.
14. Run the application and fix errors.
15. Verify the complete end-to-end demo flow.

Do not stop after creating a skeleton.

I want a **working runnable implementation**, not pseudocode.

Use official documentation for LiveKit and Razorpay integrations where needed:

- LiveKit: https://livekit.com/
- LiveKit Agents documentation: https://docs.livekit.io/agents/
- Razorpay API documentation: https://razorpay.com/docs/api/
- Razorpay Payment Links: https://razorpay.com/docs/api/payments/payment-links/
- Razorpay Webhooks: https://razorpay.com/docs/webhooks/

If an API/library has changed, use its current official documentation rather than relying on outdated examples.

---

# 35. DEFINITION OF DONE

Consider the project complete only when:

- [ ] Frontend and backend are separate.
- [ ] Dashboard works.
- [ ] MongoDB connection works.
- [ ] Seed script creates the five demo customers.
- [ ] Policy engine works independently.
- [ ] Policy engine has automated tests.
- [ ] LiveKit browser voice connection works.
- [ ] Voice agent understands Hinglish.
- [ ] Agent can retrieve customer context.
- [ ] Agent can distinguish known vs unknown customers.
- [ ] Agent can identify customer intent.
- [ ] Agent can identify payment issues.
- [ ] Agent respects policy decisions.
- [ ] Agent can create Razorpay Test Mode Payment Links when allowed.
- [ ] Agent cannot create arbitrary links when policy denies it.
- [ ] Razorpay webhook works.
- [ ] Successful payment updates MongoDB.
- [ ] Dashboard updates recovered revenue.
- [ ] Audit trail is recorded.
- [ ] Promise-to-pay is recorded.
- [ ] Escalation scenarios work.
- [ ] Bounded recovery limits work.
- [ ] README contains complete setup instructions.
- [ ] README contains all demo voice conversations.
- [ ] README explains every policy.
- [ ] `.env.example` exists.
- [ ] No secrets are committed.
- [ ] Application can be run locally using documented commands.

---

# FINAL HACKATHON REVIEW PASS

After the first implementation is complete, act as a hackathon judge.

Review the entire implementation against **Razorpay Track 03: AI Revenue Recovery**.

Identify anything that makes this look like a generic voice chatbot rather than a genuine revenue recovery agent.

Then implement the highest-impact improvements, especially around:

- Measurable revenue recovered
- Policy decisions
- Bounded autonomy
- Auditability
- Escalation
- Stopping rules
- Root-cause analysis
- Customer verification
- Promise-to-pay
- End-to-end Razorpay payment recovery
- Clear dashboard visualization

The final result should make it obvious that:

> **The voice interaction is the interface, but the actual product is an intelligent, policy-driven revenue recovery system.**
