"""
AI Revenue Recovery Voice Agent (LiveKit Agents SDK v1.x)
=========================================================
This agent handles real-time voice conversations in Hinglish.

Architecture:
  LiveKit Room (browser mic) → Voice Agent (this file) → LLM (Gemini)
                                     ↓
                              Structured Signals
                                     ↓
                           Deterministic Policy Engine
                                     ↓
                     RECOVER / CLARIFY / ESCALATE / STOP

The LLM understands the conversation.
The Policy Engine makes the final decision.

API Change Note (v0.x → v1.x):
  - VoiceAssistant            → AgentSession + Agent
  - llm.FunctionContext       → plain class with @function_tool methods
  - @llm.ai_callable          → @function_tool
  - assistant.start(room)     → session.start(ctx, agent)
  - assistant.say(...)        → session.say(...)
"""
import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from typing import Optional

# Allow running from backend directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, elevenlabs, silero
from livekit.plugins import google as livekit_google

from app.database.mongodb import connect_db
from app.services.recovery_service import (
    get_customer,
    evaluate_recovery_policy,
    create_recovery_payment_link,
    record_promise_to_pay,
    mark_escalated,
    log_audit_event,
    update_customer_recovery,
)
from app.models.policy import ConversationSignals
from app.models.customer import AuditEvent, AuditEventType
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — sets the Hinglish agent persona
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are an AI Revenue Recovery Agent for a fintech company that uses Razorpay for payments.

Your persona:
- Professional, empathetic, and respectful Indian customer support representative.
- You speak naturally in Hinglish (mix of Hindi and English).
- You never pressure the customer aggressively.
- You ask ONE question at a time.
- You listen carefully before responding.
- You never invent payment or invoice information.
- All information comes strictly from the customer database.

Your goal:
- Understand why the customer's payment failed or is overdue.
- Verify the customer's identity and payment context.
- Understand their intent (willing to pay, can't pay right now, disputes the invoice, etc.).
- Based on the conversation, extract structured signals for the Policy Engine.
- The Policy Engine (not you) makes the final decision about whether to create a payment link.

CRITICAL RULES:
1. NEVER create, mention, or promise a payment link unless the Policy Engine approves it.
2. NEVER accept the customer's stated amount if it differs from the database amount.
3. NEVER change the registered phone/email contact.
4. NEVER claim payment succeeded unless the webhook confirms it.
5. If a customer disputes the invoice, say you are escalating to the team.
6. If a customer refuses to pay, note it respectfully and end the conversation.
7. If you cannot verify the customer, escalate.

Example Hinglish phrases to use naturally:
- "Namaste [Name], main AI Revenue Recovery team se bol raha hoon."
- "Aapke account par [amount] ka payment pending hai."
- "Kya aap iske baare mein baat karna chahenge?"
- "Samajh gaya. Main check karta hoon."
- "Bilkul, main aapke registered contact par secure payment link bhej raha hoon."
- "Aapki baat samajh aai. Main ise escalate kar raha hoon hamare team ke paas."

Recovery workflow stages:
1. Greet customer by name (from database).
2. State the payment issue and amount (from database only).
3. Ask if they want to discuss the payment.
4. Listen to their situation.
5. Ask verification questions based on their context.
6. Determine their intent.
7. Report intent to Policy Engine via tool calls.
8. Follow the policy decision.
"""

# ---------------------------------------------------------------------------
# Agent class — tools are methods decorated with @function_tool
# ---------------------------------------------------------------------------

class RecoveryAgent(Agent):
    """Voice agent that handles the full recovery conversation workflow."""

    def __init__(self, customer_id: str, initial_message: str):
        super().__init__(instructions=SYSTEM_PROMPT)
        self.customer_id = customer_id
        self.initial_message = initial_message
        self._customer_data = None
        self._signals = ConversationSignals()

    async def on_enter(self):
        """Called when the agent session starts — speak the opening line."""
        await self.session.say(self.initial_message, allow_interruptions=True)

    async def _get_customer_data(self):
        if not self._customer_data:
            self._customer_data = await get_customer(self.customer_id)
        return self._customer_data

    # -----------------------------------------------------------------------
    # Tool functions (called by the LLM — backed by backend services)
    # -----------------------------------------------------------------------

    @function_tool
    async def get_customer_info(self) -> str:
        """
        Get the customer's basic information from the database. Call this first.
        Returns customer_id, name, invoice_id, amount_due, payment_status,
        failure_reason, days_overdue, previous_attempts, and risk_level.
        """
        customer = await self._get_customer_data()
        if not customer:
            return json.dumps({"error": "Customer not found in database. Cannot proceed."})
        return json.dumps({
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "invoice_id": customer["invoice_id"],
            "amount_due": customer["amount_due"],
            "payment_status": customer["payment_status"],
            "failure_reason": customer.get("failure_reason", "NONE"),
            "days_overdue": customer.get("days_overdue", 0),
            "previous_attempts": customer.get("previous_attempts", 0),
            "risk_level": customer.get("risk_level", "MEDIUM"),
        })

    @function_tool
    async def get_recovery_state(self) -> str:
        """
        Get the current recovery state and history for this customer.
        Returns status, call_attempts, payment_links_generated, current_decision,
        promise_to_pay, escalated flag, and amount_recovered.
        """
        customer = await self._get_customer_data()
        if not customer:
            return json.dumps({"error": "Customer not found"})
        rs = customer.get("recovery_state", {})
        return json.dumps({
            "status": rs.get("status"),
            "call_attempts": rs.get("call_attempts", 0),
            "payment_links_generated": rs.get("payment_links_generated", 0),
            "current_decision": rs.get("current_decision"),
            "promise_to_pay": rs.get("promise_to_pay"),
            "escalated": rs.get("escalated", False),
            "amount_recovered": rs.get("amount_recovered", 0),
        })

    @function_tool
    async def report_conversation_signals(
        self,
        customer_verified: bool = False,
        willing_to_pay: bool = False,
        dispute_raised: bool = False,
        contact_change_requested: bool = False,
        promise_to_pay: bool = False,
        promise_date: str = "",
        refused_to_pay: bool = False,
        amount_mismatch: bool = False,
        customer_stated_amount: float = 0.0,
        unknown_customer: bool = False,
        reason_given: str = "",
    ) -> str:
        """
        Report the customer's verified intent and conversation signals to the
        Policy Engine. This triggers the deterministic policy evaluation.
        IMPORTANT: All boolean fields default to False. Only set to True if
        you are CERTAIN from the conversation.
        """
        self._signals = ConversationSignals(
            customer_verified=customer_verified,
            willing_to_pay=willing_to_pay,
            dispute_raised=dispute_raised,
            contact_change_requested=contact_change_requested,
            promise_to_pay=promise_to_pay,
            promise_date=promise_date if promise_date else None,
            refused_to_pay=refused_to_pay,
            amount_mismatch=amount_mismatch,
            customer_stated_amount=customer_stated_amount if customer_stated_amount > 0 else None,
            unknown_customer=unknown_customer,
            reason_given=reason_given if reason_given else None,
        )

        result = await evaluate_recovery_policy(self.customer_id, self._signals)
        if result is None:
            return json.dumps({"error": "Policy evaluation failed — customer not found"})

        logger.info(f"🎯 Policy decision for {self.customer_id}: {result['decision']}")
        return json.dumps({
            "policy_decision": result["decision"],
            "reason": result["reason"],
            "can_create_payment_link": result["can_create_payment_link"],
            "can_resend_payment_link": result["can_resend_payment_link"],
            "should_escalate": result["should_escalate"],
            "should_stop": result["should_stop"],
            "recovery_score": result["recovery_score"],
        })

    @function_tool
    async def create_payment_link(self) -> str:
        """
        Create a Razorpay payment link. ONLY call this if the policy decision
        was RECOVER_NOW. The amount is ALWAYS taken from the database — never
        from the customer's verbal statement. Do NOT call this if policy
        decision is anything other than RECOVER_NOW.
        """
        result = await create_recovery_payment_link(self.customer_id)
        if result is None:
            return json.dumps({"error": "Customer not found"})
        if "error" in result:
            return json.dumps({
                "error": result["error"],
                "policy_decision": result.get("decision"),
                "reason": result.get("reason"),
            })

        customer = await self._get_customer_data()
        customer_name = customer["name"] if customer else "the customer"
        return json.dumps({
            "success": True,
            "link_id": result["link_id"],
            "short_url": result["short_url"],
            "amount": result["amount"],
            "message": (
                f"Payment link created for ₹{result['amount']:,.0f}. "
                f"Link will be sent to {customer_name}'s registered contact."
            ),
        })

    @function_tool
    async def record_promise_to_pay(
        self,
        promise_date: str,
        amount: float,
    ) -> str:
        """
        Record a promise-to-pay when the customer says they will pay on a
        specific future date. Extract the date from the conversation in
        YYYY-MM-DD format.
        """
        success = await record_promise_to_pay(self.customer_id, promise_date, amount)
        if not success:
            return json.dumps({"error": "Failed to record promise-to-pay"})
        return json.dumps({
            "success": True,
            "promise_date": promise_date,
            "amount": amount,
            "message": f"Promise-to-pay recorded for {promise_date}. No immediate payment link.",
        })

    @function_tool
    async def escalate_to_human(self, reason: str) -> str:
        """
        Escalate the case to a human agent. Call this when policy decision is
        ESCALATE, or when the customer disputes the invoice, requests a contact
        change, or cannot be verified.
        """
        success = await mark_escalated(self.customer_id, reason)
        if not success:
            return json.dumps({"error": "Failed to escalate"})
        return json.dumps({
            "success": True,
            "reason": reason,
            "message": "Case escalated to human team. No automated payment link will be created.",
        })


# ---------------------------------------------------------------------------
# Agent entrypoint
# ---------------------------------------------------------------------------

async def entrypoint(ctx: JobContext):
    """Main LiveKit agent entrypoint."""
    # Connect to MongoDB
    await connect_db()

    # Extract customer_id from room metadata or name
    room_name = ctx.room.name  # e.g. "recovery-CUS_001"
    customer_id = room_name.replace("recovery-", "") if room_name.startswith("recovery-") else "CUS_001"

    logger.info(f"🎙️  Voice agent starting for room: {room_name}, customer: {customer_id}")

    # Fetch initial customer context
    # Note: ctx.connect() is called automatically by session.start() internally
    customer = await get_customer(customer_id)
    if not customer:
        logger.error(f"❌ Customer {customer_id} not found in database")
        customer = {"name": "Unknown", "amount_due": 0, "payment_status": "UNKNOWN", "invoice_id": "UNKNOWN"}

    # Build context-aware initial message
    initial_message = (
        f"Namaste {customer['name']}, main AI Revenue Recovery team se bol raha hoon. "
        f"Aapke account par ₹{customer['amount_due']:,.0f} ka payment pending hai "
        f"invoice {customer['invoice_id']} ke liye. "
        f"Kya aap iske baare mein baat karna chahenge?"
    )

    # Log call started
    await log_audit_event(AuditEvent(
        customer_id=customer_id,
        invoice_id=str(customer.get("invoice_id", "UNKNOWN")),
        event=AuditEventType.CALL_STARTED,
        actor="SYSTEM",
        reason=f"Voice recovery call started in room {room_name}",
    ))

    # Inject customer context into the system prompt
    customer_ctx = json.dumps(
        {k: v for k, v in customer.items() if k not in ("recovery_state", "_id")},
        indent=2,
        default=str,
    )
    full_instructions = SYSTEM_PROMPT + f"\n\nCurrent customer context:\n{customer_ctx}"

    # Build the agent (instructions set dynamically with customer context)
    agent = RecoveryAgent(
        customer_id=customer_id,
        initial_message=initial_message,
    )
    agent._instructions = full_instructions  # override with customer-specific context

    # Create and start the session
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-2",
            language="en-IN",   # Indian English — best for Hinglish
        ),
        llm=livekit_google.LLM(
            model="gemini-2.0-flash-exp",
            api_key=settings.GOOGLE_API_KEY,
        ),
        tts=elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY,
            voice_id=settings.ELEVENLABS_VOICE_ID,
            model="eleven_multilingual_v2",  # Supports Hindi
        ),
    )

    # In v1.7, session.start() takes agent as the first positional arg.
    # The JobContext (room connection) is discovered automatically via get_job_context().
    await session.start(agent)

    # Log call ended on disconnect
    @ctx.room.on("participant_disconnected")
    def on_disconnect(participant):
        logger.info(f"Participant disconnected: {participant.identity}")
        asyncio.create_task(
            log_audit_event(AuditEvent(
                customer_id=customer_id,
                invoice_id=str(customer.get("invoice_id", "UNKNOWN")),
                event=AuditEventType.CALL_ENDED,
                actor="SYSTEM",
                reason="Voice call ended",
            ))
        )


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
