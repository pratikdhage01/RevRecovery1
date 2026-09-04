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

# Ensure backend directory is in sys.path so 'app' package is importable
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

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
    function_tool,
)
from livekit.agents._exceptions import APIStatusError
from livekit.agents.cli import run_app
from livekit.agents import llm as agents_llm
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


class FallbackLLM(agents_llm.LLM):
    """
    Wraps a primary Google LLM and transparently falls back to a secondary
    model when the primary returns a 503 (high-demand / unavailable) error.

    Usage:
        llm = FallbackLLM(
            primary=livekit_google.LLM(model="gemini-3.1-flash-lite", ...),
            fallback=livekit_google.LLM(model="gemini-2.0-flash", ...),
        )
    """

    def __init__(
        self,
        primary: agents_llm.LLM,
        fallback: agents_llm.LLM,
    ):
        super().__init__()
        self._primary = primary
        self._fallback = fallback

    def chat(
        self,
        *,
        chat_ctx: agents_llm.ChatContext,
        tools: list | None = None,
        **kwargs,
    ) -> agents_llm.LLMStream:
        """Try primary; on 503 fall back to secondary model."""
        try:
            stream = self._primary.chat(chat_ctx=chat_ctx, tools=tools, **kwargs)
            return _FallbackStream(stream, self._fallback, chat_ctx, tools, kwargs)
        except APIStatusError as e:
            if e.status_code == 503:
                logger.warning(
                    f"Primary LLM unavailable (503), switching to fallback model. error={e}"
                )
                return self._fallback.chat(chat_ctx=chat_ctx, tools=tools, **kwargs)
            raise


class _FallbackStream(agents_llm.LLMStream):
    """
    Wraps a primary LLMStream and switches to the fallback LLM
    mid-stream if a 503 is encountered during async iteration.
    """

    def __init__(self, primary_stream, fallback_llm, chat_ctx, tools, kwargs):
        super().__init__(primary_stream._llm, chat_ctx=chat_ctx, tools=tools or [], conn_options=primary_stream._conn_options)
        self._primary_stream = primary_stream
        self._fallback_llm = fallback_llm
        self._chat_ctx = chat_ctx
        self._tools = tools
        self._kwargs = kwargs

    async def _run(self) -> None:
        try:
            async for chunk in self._primary_stream:
                self._event_ch.send_nowait(chunk)
        except APIStatusError as e:
            if e.status_code == 503:
                logger.warning(
                    f"Primary LLM stream failed mid-response (503), "
                    f"retrying with fallback model. error={e}"
                )
                fallback_stream = self._fallback_llm.chat(
                    chat_ctx=self._chat_ctx,
                    tools=self._tools,
                    **self._kwargs,
                )
                async for chunk in fallback_stream:
                    self._event_ch.send_nowait(chunk)
            else:
                raise

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

CONVERSATION FLOW:
1. Turn 1 (Greeting):
   You greet the customer by name, mention the pending invoice and amount, and ask if they can discuss it.
2. Turn 2 (Listen & Propose Alternative):
   When customer mentions card failed or payment issue, empathetically acknowledge in Hinglish and ask:
   "Samajh gaya. Aapki card payment fail ho gayi hai. Kya aap alternative payment method se payment complete karna chahenge? Jaise UPI ya netbanking?"
3. Turn 3 (Execute & Confirm Link):
   When customer agrees to pay via UPI or alternative method (e.g. "may upi se kar skta hu", "haan upi se kar do", "theek hai"):
   - Call confirm_payment_intent_and_create_link()
   - Speak back to customer immediately:
     "Bahut badiya! Maine aapka verification complete kar diya hai aur aapke registered mobile number aur email par secure Razorpay UPI payment link bhej diya hai. Aap wahan se payment complete kar sakte hain."
4. Turn 4 (Closing):
   When customer confirms or thanks you (e.g. "link mil gaya", "payment kar raha hoon", "thank you"):
   - Say: "Shukriya! Jaise hi payment complete hogi, aapka account update ho jayega. Have a great day!"

CRITICAL RULES:
1. ALWAYS speak aloud back to the customer on every turn. Never finish your turn silently.
2. Keep replies natural, polite, and concise (1-3 sentences).
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
    async def confirm_payment_intent_and_create_link(self) -> str:
        """
        Call this when the customer verifies their identity and agrees to pay
        (e.g., via UPI, netbanking, or alternative payment method).
        This reports verified intent to the Policy Engine and creates the Razorpay payment link.
        """
        logger.info(f"🎯 [Tool: confirm_payment_intent_and_create_link] Processing for {self.customer_id}")
        self._signals = ConversationSignals(
            customer_verified=True,
            willing_to_pay=True,
        )
        policy_result = await evaluate_recovery_policy(self.customer_id, self._signals)
        if not policy_result:
            return json.dumps({"error": "Policy evaluation failed"})

        logger.info(f"🎯 Policy decision for {self.customer_id}: {policy_result['decision']}")
        if not policy_result.get("can_create_payment_link"):
            return json.dumps({
                "policy_decision": str(policy_result["decision"]),
                "reason": policy_result["reason"],
                "can_create_payment_link": False,
            })

        link_result = await create_recovery_payment_link(self.customer_id)
        if not link_result or "error" in link_result:
            error_msg = link_result.get("error", "Failed to create payment link") if link_result else "Failed"
            return json.dumps({"error": error_msg})

        customer = await self._get_customer_data()
        amount = customer["amount_due"] if customer else 2499
        logger.info(f"✅ [Tool: confirm_payment_intent_and_create_link] Payment link created: {link_result.get('short_url')}")
        return json.dumps({
            "success": True,
            "policy_decision": "RECOVER_NOW",
            "amount": amount,
            "short_url": link_result.get("short_url"),
            "message": f"Payment link created for INR {amount}. Sent to customer registered mobile and email.",
        })

    @function_tool
    async def get_customer_info(self) -> str:
        """
        Get the customer's basic information from the database if needed.
        Note: Customer details are already in the system prompt.
        """
        logger.info(f"🔍 [Tool: get_customer_info] Fetching info for {self.customer_id}")
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
        logger.info(f"🔍 [Tool: get_recovery_state] Fetching recovery state for {self.customer_id}")
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
        logger.info(f"📊 [Tool: report_conversation_signals] verified={customer_verified}, willing={willing_to_pay}, dispute={dispute_raised}")
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
        logger.info(f"💳 [Tool: create_payment_link] Generating link for {self.customer_id}")
        result = await create_recovery_payment_link(self.customer_id)
        if result is None:
            return json.dumps({"error": "Customer not found"})
        if "error" in result:
            logger.warning(f"⚠️ [Tool: create_payment_link] Failed: {result['error']}")
            return json.dumps({
                "error": result["error"],
                "policy_decision": result.get("decision"),
                "reason": result.get("reason"),
            })

        customer = await self._get_customer_data()
        customer_name = customer["name"] if customer else "the customer"
        logger.info(f"✅ [Tool: create_payment_link] Created: {result.get('short_url')}")
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
    logger.info("🚀 Entrypoint called — connecting to MongoDB")
    await connect_db()

    # Extract customer_id from room name, e.g. "recovery-CUS_001"
    room_name = ctx.room.name
    customer_id = room_name.replace("recovery-", "") if room_name.startswith("recovery-") else "CUS_001"

    logger.info(f"🎙️  Voice agent starting for room: {room_name}, customer: {customer_id}")

    # NOTE: Do NOT call ctx.connect() here.
    # session.start(agent, room=ctx.room) first starts RoomIO (which sets up
    # audio input/output listeners), then calls job_ctx.connect() internally.
    # If we connect early, RoomIO is not yet set up when existing participants
    # are processed, and the browser's microphone track is silently missed —
    # the agent would speak but never hear the user.

    # Fetch initial customer context
    customer = await get_customer(customer_id)
    if not customer:
        logger.error(f"❌ Customer {customer_id} not found in database")
        customer = {"name": "Unknown", "amount_due": 0, "payment_status": "UNKNOWN", "invoice_id": "UNKNOWN"}
    else:
        logger.info(f"✅ Customer loaded: {customer['name']}, amount: {customer['amount_due']}")

    # Build context-aware initial message (Hinglish)
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

    # Build the agent with full customer-specific instructions
    agent = RecoveryAgent(
        customer_id=customer_id,
        initial_message=initial_message,
    )
    # Override instructions with customer-specific context
    agent._instructions = full_instructions

    logger.info("🤖 Creating AgentSession (VAD + STT + LLM + TTS)")
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-2",
            language="en-IN",   # Indian English — best for Hinglish
        ),
        llm=FallbackLLM(
            primary=livekit_google.LLM(
                model="gemini-3.1-flash-lite",
                api_key=settings.GOOGLE_API_KEY,
            ),
            fallback=livekit_google.LLM(
                model="gemini-2.0-flash",
                api_key=settings.GOOGLE_API_KEY,
            ),
        ),
        tts=elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY,
            voice_id=settings.ELEVENLABS_VOICE_ID,
            model="eleven_multilingual_v2",  # Supports Hindi
        ),
        max_tool_steps=8,
    )

    # CRITICAL: pass room=ctx.room so AgentSession creates RoomIO and wires up
    # audio I/O. Without this, no RoomIO is created and the agent never speaks.
    # The on_enter() method on RecoveryAgent handles the initial greeting.
    logger.info("▶️  Starting AgentSession with room IO")
    await session.start(agent, room=ctx.room)
    logger.info("✅ AgentSession started — agent should now speak")

    # Log call ended on disconnect
    @ctx.room.on("participant_disconnected")
    def on_disconnect(participant):
        logger.info(f"📴 Participant disconnected: {participant.identity}")
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
    run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
