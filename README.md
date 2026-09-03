# AI Revenue Recovery Agent 🎯
### Find revenue that's slipping away and win it back

An **intelligent, policy-driven revenue recovery system** with Hinglish voice interaction, deterministic decision authority, and real-time Razorpay payment recovery.

> **The voice interaction is the interface. The actual product is a policy-driven recovery system.**

---

## Architecture

```
Browser (Next.js Dashboard)
    │
    ├── GET /api/customers → Customer Recovery Table
    ├── GET /api/dashboard/stats → Revenue Metrics
    │
    ├── POST /api/livekit/token ──────────────────┐
    │                                             ▼
    │                                   LiveKit Room
    │                                       │
    │                                       ▼
    │                              Voice Agent (Python)
    │                                       │
    │                               LLM (Gemini 2.0)
    │                                       │
    │                           Structured Conversation Signals
    │                                       │
    │                           DETERMINISTIC POLICY ENGINE
    │                              ┌────────┼────────┐
    │                              ▼        ▼        ▼
    │                           RECOVER  CLARIFY  ESCALATE
    │                              │
    │                              ▼
    │                       FastAPI Backend
    │                              │
    │                       Razorpay API (Test)
    │                              │
    │                       Payment Link Created
    │                              │
    │                       Razorpay Webhook
    │                              │
    │                       MongoDB Updated
    │                              │
    └── Dashboard Auto-refresh → Revenue Recovered
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Python 3.13, FastAPI |
| Voice Agent | LiveKit Agents SDK |
| LLM | Google Gemini (gemini-2.0-flash) |
| STT | Deepgram (nova-2, en-IN) |
| TTS | ElevenLabs (eleven_multilingual_v2) |
| VAD | Silero VAD |
| Database | MongoDB (Motor async driver) |
| Payment | Razorpay Test Mode |
| Package Manager | uv (Python), npm (Node.js) |

---

## Project Structure

```
ai-revenue-recovery/
│
├── frontend/                      # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx               # Main dashboard
│   │   ├── customers/[id]/page.tsx # Customer detail + voice agent
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── lib/api.ts                  # API client + TypeScript types
│   ├── .env.local
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint
│   │   ├── core/config.py         # Pydantic-settings configuration
│   │   ├── database/mongodb.py    # Motor async connection
│   │   ├── models/
│   │   │   ├── customer.py        # All DB models + enums
│   │   │   └── policy.py          # Policy models + ConversationSignals
│   │   ├── policies/
│   │   │   └── recovery_policy.py # DETERMINISTIC POLICY ENGINE
│   │   ├── services/
│   │   │   ├── recovery_service.py # Recovery orchestration
│   │   │   └── razorpay_service.py # Razorpay API wrapper
│   │   ├── api/
│   │   │   ├── customers.py       # Customer endpoints
│   │   │   ├── recovery.py        # Recovery endpoints
│   │   │   ├── dashboard.py       # Stats endpoint
│   │   │   └── livekit_token.py   # Token generation
│   │   ├── webhooks/
│   │   │   └── razorpay_webhook.py # Webhook handler
│   │   └── agents/
│   │       └── voice_agent.py     # LiveKit voice agent
│   ├── scripts/
│   │   └── seed_customers.py      # Demo data seeder
│   ├── tests/
│   │   └── test_policy_engine.py  # 25 policy engine tests
│   ├── requirements.txt
│   └── .env.example
│
├── .gitignore
└── README.md
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in values.

```bash
cp backend/.env.example backend/.env
```

| Variable | Description |
|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | Database name (default: `revenue_recovery`) |
| `RAZORPAY_KEY_ID` | Razorpay Test Mode Key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay Test Mode Key Secret |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay webhook signature secret |
| `LIVEKIT_URL` | LiveKit server URL (wss://...) |
| `LIVEKIT_API_KEY` | LiveKit API Key |
| `LIVEKIT_API_SECRET` | LiveKit API Secret |
| `GOOGLE_API_KEY` | Google AI Studio API key (Gemini) |
| `DEEPGRAM_API_KEY` | Deepgram API key |
| `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `MAX_CALL_ATTEMPTS` | Max recovery calls per customer (default: 2) |
| `MAX_PAYMENT_LINKS` | Max payment links per customer (default: 2) |
| `MAX_RECOVERY_DAYS` | Recovery window in days (default: 7) |
| `AUTO_RECOVERY_LIMIT` | Auto-recovery max amount INR (default: 5000) |
| `HIGH_VALUE_THRESHOLD` | Human escalation threshold INR (default: 25000) |

---

## Setup

### 1. MongoDB Setup
1. Create a free cluster at [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a database user and whitelist your IP
3. Copy the connection string to `MONGODB_URI`

### 2. LiveKit Setup
1. Create a free project at [LiveKit Cloud](https://cloud.livekit.io)
2. Copy URL, API Key, and API Secret to `.env`
3. The voice agent will connect to your LiveKit room automatically

### 3. Razorpay Test Mode Setup
1. Log in to [Razorpay Dashboard](https://dashboard.razorpay.com)
2. Switch to **Test Mode**
3. Go to Settings → API Keys → Generate Test Key
4. Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` to `.env`

### 4. Razorpay Webhook Setup
1. Go to Razorpay Dashboard → Webhooks
2. Create webhook pointing to: `https://your-domain/api/webhooks/razorpay`
3. Subscribe to: `payment_link.paid`, `payment.captured`
4. Copy the webhook secret to `RAZORPAY_WEBHOOK_SECRET`
5. For local testing, use [ngrok](https://ngrok.com): `ngrok http 8000`

---

## Running the Application

### Install Python Dependencies
```bash
uv pip install -r backend/requirements.txt
```

### Seed the Database
```bash
cd backend
python scripts/seed_customers.py
```

Expected output:
```
Inserted: CUS_001 — Rahul Sharma
Inserted: CUS_002 — Priya Mehta
Inserted: CUS_003 — Amit Enterprises
Inserted: CUS_004 — Neha Joshi
Inserted: CUS_005 — Arjun Kapoor
```

### Start the Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Start the Voice Agent (separate terminal)
```bash
cd backend
python app/agents/voice_agent.py start
```

### Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Running Tests

```bash
cd backend
pytest tests/test_policy_engine.py -v
```

Expected: **25 passed**

---

## Policy Engine

The deterministic policy engine (`backend/app/policies/recovery_policy.py`) makes all final decisions. **The LLM cannot override these.**

### Architecture Principle

```
LLM (Gemini)              → Understands Hinglish
                          → Extracts intent
                          → Identifies root cause
                          → Extracts promise-to-pay dates
                          → Recommends action
                             ↓
                    ConversationSignals (structured)
                             ↓
        DETERMINISTIC POLICY ENGINE (Python)
                             ↓
                      PolicyDecision
                  (LLM cannot change this)
```

### Policy Rules (Priority Order)

| Priority | Condition | Decision |
|---|---|---|
| 1 | `payment_status == PAID` | `STOP_PAID` |
| 2 | `amount_due <= 0` | `STOP_NO_DUE` |
| 3 | Unknown customer | `ESCALATE` |
| 4 | Contact change requested | `ESCALATE` |
| 5 | Invoice dispute raised | `ESCALATE` |
| 6 | Customer refuses to pay | `STOP_REFUSED` |
| 7 | Amount mismatch (customer vs DB) | `CLARIFY` |
| 8 | `call_attempts >= MAX_CALL_ATTEMPTS` | `STOP_MAX_ATTEMPTS` |
| 9 | `recovery_days > MAX_RECOVERY_DAYS` | `STOP_WINDOW_EXPIRED` |
| 10 | Promise to pay | `TRACK_PROMISE_TO_PAY` |
| 11a | Verified + willing + active link | `RESEND_EXISTING_LINK` |
| 11b | Verified + willing + amount > 25000 | `ESCALATE` |
| 11c | Verified + willing + 5001-25000 | `NEEDS_ADDITIONAL_VERIFICATION` |
| 11d | Verified + willing + amount ≤ 5000 | `RECOVER_NOW` |
| default | Not verified / unknown intent | `CLARIFY` |

---

## Recovery Decision Matrix

| Situation | Decision |
|---|---|
| Already paid | STOP_PAID |
| No amount due | STOP_NO_DUE |
| Verified + willing to pay | RECOVER_NOW |
| Existing active link | RESEND_EXISTING_LINK |
| Payment method failed | ALTERNATIVE_RECOVERY |
| Promise to pay | TRACK_PROMISE_TO_PAY |
| Invoice dispute | ESCALATE |
| Identity mismatch | ESCALATE |
| High-value transaction (>₹25K) | ESCALATE |
| Contact change | ESCALATE |
| Max attempts reached | STOP_MAX_ATTEMPTS |
| Recovery window expired | STOP_WINDOW_EXPIRED |
| Unknown customer | ESCALATE |
| Customer refuses | STOP_REFUSED |

---

## Demo Voice Conversations

Use these scripts while demoing the voice agent.

### Scenario 1 — Successful Recovery (Rahul Sharma, CUS_001)

```
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
Bilkul. Main check karta hoon... [calls policy engine]
Aapka verification complete ho gaya hai aur amount ₹2,499 confirm hai.
Main aapke registered contact par secure Razorpay payment link bhej raha hoon.

Expected system flow:
→ Customer verified (matched invoice + context)
→ Willing to pay confirmed
→ Policy: RECOVER_NOW
→ Payment link created (₹2,499 from DB — not from customer)
→ Webhook awaited for payment confirmation
```

---

### Scenario 2 — Promise to Pay (Priya Mehta, CUS_002)

```
AI:
Namaste Priya, main AI Revenue Recovery team se bol raha hoon.
Aapke account par ₹4,999 ka payment 5 din se overdue hai.
Kya aap iske baare mein baat karna chahenge?

You:
Haan, but abhi payment nahi kar sakti.
Kal salary aayegi, kal payment kar dungi.

AI:
Samajh aaya. Koi problem nahi. Kya aap kal payment kar sakti hain?

You:
Haan, kal pakka.

AI:
Theek hai. Main aapka promise-to-pay record kar raha hoon kal ke liye.
Koi pressure nahi. Agar koi help chahiye toh hum contact karenge.

Expected system flow:
→ Promise-to-pay detected: tomorrow's date extracted
→ Policy: TRACK_PROMISE_TO_PAY
→ PTP stored in MongoDB
→ NO payment link created
→ Dashboard shows "Promise to Pay" status
```

---

### Scenario 3 — Invoice Dispute (Amit Enterprises, CUS_003)

```
AI:
Namaste, main Amit Enterprises ke liye AI Revenue Recovery team se hoon.
₹18,500 ka invoice INV_003 overdue hai.

You:
Ye invoice galat hai. Humne ye service approve hi nahi ki thi.
Ye amount galat hai.

AI:
Samajh gaya. Aap invoice dispute kar rahe hain. Main ye case hamare
human review team ke paas escalate kar raha hoon.
Koi automated payment link generate nahi hoga.
Aapको ek confirmation email aayega.

Expected system flow:
→ Dispute detected in conversation
→ Policy: ESCALATE
→ NO payment link generated
→ Case marked ESCALATED in dashboard
→ Audit event: ESCALATED_TO_HUMAN
```

---

### Scenario 4 — Already Paid (Neha Joshi, CUS_004)

```
AI:
Namaste Neha, main AI Revenue Recovery team se hoon.
[checks database]

System (immediately):
→ payment_status == PAID
→ Policy: STOP_PAID
→ Agent says: "Aapka payment pehle se complete hai. Koi action required nahi."

Expected system flow:
→ STOP_PAID before call even starts
→ Agent informs customer politely
→ No new payment link
```

---

### Scenario 5 — High-Value Transaction (Arjun Kapoor, CUS_005)

```
AI:
Namaste Arjun, main AI Revenue Recovery team se hoon.
Aapke account par ₹75,000 ka payment pending hai.

You:
Haan main payment karna chahta hoon, mera payment method fail hua tha.

AI:
Samajh gaya. Lekin ₹75,000 ek high-value transaction hai.
Iske liye humara senior team verify karega aur aapse contact karega.
Automated recovery is amount ke liye allowed nahi hai.

Expected system flow:
→ Customer verified + willing
→ Amount ₹75,000 > HIGH_VALUE_THRESHOLD (₹25,000)
→ Policy: ESCALATE
→ NO automated payment link (policy blocks it)
→ Human escalation required
```

---

### Scenario 6 — Contact Change Attempt

```
You:
Payment link mere naye number pe bhej do — 9999988888.

AI:
Maafi chahta hoon, lekin registered contact details change karna
is call mein possible nahi hai security reasons se.
Ye case hamare team ke paas escalate kar raha hoon.

Expected system flow:
→ Contact change detected
→ Policy: ESCALATE (regardless of other signals)
→ NO payment link
→ Audit: CONTACT_CHANGE_BLOCKED
```

---

### Scenario 7 — Unknown Customer

```
You:
Mera ₹5,000 ka payment pending hai.

System:
→ Customer not found in database
→ Policy: ESCALATE
→ Agent cannot find any matching record
→ DO NOT create payment link
→ Ask for verification context
→ If still unresolved → ESCALATE
```

---

### Scenario 8 — Amount Mismatch

```
Database: ₹2,499

You:
Mera ₹4,999 ka payment pending hai.

AI:
Humara record ₹2,499 dikhata hai aapke invoice ke liye.
₹4,999 match nahi kar raha. Kya aap invoice number confirm kar sakte hain?

Expected system flow:
→ Amount mismatch detected (₹4,999 ≠ ₹2,499 in DB)
→ Policy: CLARIFY
→ NO payment link for ₹4,999
→ NO payment link at all until clarified
```

---

### Scenario 9 — Customer Refuses

```
You:
Mujhe payment nahi karna. Main nahi karunga.

AI:
Theek hai, koi pressure nahi hai. Main aapki baat samajhta hoon.
Aapka refusal record kar raha hoon. Agar kabhi zaroorat ho toh hume contact karen.

Expected system flow:
→ Refusal detected
→ Policy: STOP_REFUSED
→ Recovery stopped respectfully
→ Refusal recorded in audit trail
→ NO repeated contact
```

---

### Scenario 10 — Why Did Payment Fail?

```
You:
Kyun payment fail hua mera?

AI:
[fetches failure_reason from database]
Aapki card payment decline hui thi. Bank ki taraf se decline aya tha.
Iska matlab aapke card mein koi issue tha. Aap alternative method try kar sakte hain.

Expected system flow:
→ Agent retrieves failure_reason from MongoDB (CARD_DECLINED)
→ Explains without inventing details
→ Never fabricates a reason
```

---

## Audit Trail Events

Every important system action is recorded:

| Event | Trigger |
|---|---|
| `RECOVERY_STARTED` | Recovery call initiated |
| `CUSTOMER_VERIFIED` | Identity confirmed |
| `PAYMENT_CONTEXT_RETRIEVED` | DB lookup complete |
| `ROOT_CAUSE_IDENTIFIED` | Failure reason identified |
| `POLICY_EVALUATED` | Policy engine ran |
| `PAYMENT_LINK_CREATED` | Razorpay link created |
| `PAYMENT_LINK_SENT` | Link delivered |
| `PROMISE_TO_PAY_RECORDED` | PTP stored |
| `PAYMENT_RECEIVED` | Webhook confirmed payment |
| `REVENUE_RECOVERED` | Amount marked recovered |
| `RECOVERY_STOPPED` | Stopped (any reason) |
| `ESCALATED_TO_HUMAN` | Human review required |
| `CONTACT_CHANGE_BLOCKED` | Contact change attempt blocked |
| `DISPUTE_DETECTED` | Invoice dispute raised |
| `CALL_STARTED` | Voice call began |
| `CALL_ENDED` | Voice call ended |

---

## Recovery Score

Transparent, deterministic 0-100 score for prioritization:

| Factor | Max | How earned |
|---|---|---|
| Customer Intent | 30 | Willing=30, PTP=15, Refusing/Dispute=0 |
| Payment History | 20 | 0 prev=20, 1=15, 2=8, 3+=0 |
| Verification | 20 | Verified+no dispute=20, Verified=5, None=0 |
| Amount Risk | 15 | ≤₹5K=15, ≤₹25K=8, >₹25K=0 |
| Recovery Window | 15 | ≤3 days=15, ≤7=10, ≤14=5, 14+=0 |

The hard policy rules override the score. Score is for display and prioritization only.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/customers` | List all customers |
| GET | `/api/customers/{id}` | Get customer details |
| GET | `/api/customers/{id}/recovery` | Get recovery state |
| GET | `/api/customers/{id}/audit` | Get audit trail |
| GET | `/api/dashboard/stats` | Dashboard metrics |
| POST | `/api/recovery/{id}/start` | Start recovery workflow |
| POST | `/api/recovery/{id}/evaluate` | Run policy engine |
| POST | `/api/recovery/{id}/payment-link` | Create payment link (policy-gated) |
| POST | `/api/recovery/{id}/promise-to-pay` | Record PTP |
| POST | `/api/recovery/{id}/escalate` | Escalate case |
| POST | `/api/livekit/token` | Generate LiveKit token |
| POST | `/api/webhooks/razorpay` | Razorpay webhook |

---

## Security

- Razorpay secrets are server-side only
- LiveKit secrets never reach the browser
- Webhook signature verified on every event
- Payment amounts always from MongoDB (never from LLM/customer)
- Frontend cannot create payment links directly
- All payment-link creation passes through policy validation

---

## Future Improvements

- SMS/WhatsApp payment link delivery via Twilio
- Telephony integration (Twilio/Exotel) for outbound calls
- Multi-language support beyond Hinglish
- ML-based recovery probability prediction
- Automated follow-up scheduling for promise-to-pay
- Integration with CRM systems
- Real-time dashboard WebSocket updates
- Bulk recovery batch processing
- Compliance audit export (PDF/CSV)
