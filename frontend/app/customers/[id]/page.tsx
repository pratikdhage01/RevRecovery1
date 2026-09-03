'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  fetchCustomer, fetchAuditTrail, startRecovery, getLiveKitToken,
  Customer, AuditEvent
} from '@/lib/api';
import { Room, RoomEvent, Track, RemoteParticipant } from 'livekit-client';

// ── Helpers ──────────────────────────────────────────────────────────────────

const DECISION_COLORS: Record<string, string> = {
  RECOVER_NOW:                    '#10b981',
  RESEND_EXISTING_LINK:           '#3b82f6',
  ALTERNATIVE_RECOVERY:           '#6366f1',
  CLARIFY:                        '#f59e0b',
  TRACK_PROMISE_TO_PAY:           '#f59e0b',
  ESCALATE:                       '#ef4444',
  STOP_PAID:                      '#10b981',
  STOP_NO_DUE:                    '#10b981',
  STOP_MAX_ATTEMPTS:              '#ef4444',
  STOP_WINDOW_EXPIRED:            '#ef4444',
  STOP_REFUSED:                   '#94a3b8',
  NEEDS_ADDITIONAL_VERIFICATION:  '#8b5cf6',
};

const AUDIT_COLORS: Record<string, string> = {
  RECOVERY_STARTED:        '#6366f1',
  CUSTOMER_VERIFIED:       '#10b981',
  PAYMENT_CONTEXT_RETRIEVED:'#3b82f6',
  ROOT_CAUSE_IDENTIFIED:   '#f59e0b',
  POLICY_EVALUATED:        '#8b5cf6',
  PAYMENT_LINK_CREATED:    '#10b981',
  PAYMENT_LINK_SENT:       '#10b981',
  PAYMENT_LINK_RESENT:     '#3b82f6',
  PROMISE_TO_PAY_RECORDED: '#f59e0b',
  PAYMENT_RECEIVED:        '#10b981',
  REVENUE_RECOVERED:       '#10b981',
  RECOVERY_STOPPED:        '#94a3b8',
  ESCALATED_TO_HUMAN:      '#ef4444',
  CONTACT_CHANGE_BLOCKED:  '#ef4444',
  DISPUTE_DETECTED:        '#ef4444',
  RECOVERY_REFUSED:        '#94a3b8',
  CALL_STARTED:            '#6366f1',
  CALL_ENDED:              '#64748b',
};

function formatINR(n: number) {
  return `₹${n.toLocaleString('en-IN')}`;
}

function formatTime(ts: string) {
  return new Date(ts).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}

// ── Section Card ─────────────────────────────────────────────────────────────

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ marginBottom: 16, overflow: 'hidden' }}>
      <div style={{
        padding: '14px 20px',
        borderBottom: '1px solid var(--color-border)',
        fontSize: 12, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.08em', color: 'var(--color-text-muted)',
      }}>
        {title}
      </div>
      <div style={{ padding: '20px' }}>{children}</div>
    </div>
  );
}

// ── Info Row ─────────────────────────────────────────────────────────────────

function InfoRow({ label, value, accent }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border)' }}>
      <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: accent || 'var(--color-text)' }}>{value}</span>
    </div>
  );
}

// ── Score Breakdown ───────────────────────────────────────────────────────────

function ScoreBreakdown({ score, breakdown }: { score: number; breakdown: Record<string, string> }) {
  const getMax = (val: string) => parseInt(val.split('/')[1]);
  const getScore = (val: string) => parseInt(val.split('/')[0]);
  const color = score >= 80 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>Recovery Score</span>
        <span style={{ fontSize: 28, fontWeight: 800, color }}>{score}<span style={{ fontSize: 16, fontWeight: 500 }}>/100</span></span>
      </div>
      <div className="score-bar-track" style={{ marginBottom: 20 }}>
        <div className="score-bar-fill" style={{ width: `${score}%`, background: `linear-gradient(90deg, ${color}, ${color}aa)` }} />
      </div>
      {Object.entries(breakdown).filter(([k]) => k !== 'TOTAL').map(([label, val]) => (
        <div key={label} style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{label}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text)' }}>{val}</span>
          </div>
          <div className="score-bar-track" style={{ height: 4 }}>
            <div className="score-bar-fill"
              style={{ width: `${(getScore(val) / getMax(val)) * 100}%`, height: '100%', background: color }} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Policy Checks ─────────────────────────────────────────────────────────────

function PolicyChecks({ checks }: { checks: { label: string; passed: boolean; reason: string }[] }) {
  return (
    <div>
      {checks.map((c, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', borderBottom: '1px solid var(--color-border)' }}>
          <span style={{ fontSize: 15, color: c.passed ? '#10b981' : '#ef4444' }}>
            {c.passed ? '✓' : '✗'}
          </span>
          <span style={{ flex: 1, fontSize: 13, color: 'var(--color-text)' }}>{c.label}</span>
          <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{c.reason}</span>
        </div>
      ))}
    </div>
  );
}

// ── Audit Trail ──────────────────────────────────────────────────────────────

function AuditTimeline({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-text-muted)', fontSize: 13 }}>
        No audit events yet. Start a recovery call to begin.
      </div>
    );
  }
  return (
    <div style={{ maxHeight: 400, overflowY: 'auto' }}>
      {events.map((e, i) => {
        const color = AUDIT_COLORS[e.event] || '#64748b';
        return (
          <div key={i} style={{ display: 'flex', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div className="audit-dot" style={{ background: color }} />
              {i < events.length - 1 && <div style={{ width: 1, flex: 1, background: 'var(--color-border)', minHeight: 20 }} />}
            </div>
            <div style={{ flex: 1, paddingBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color, fontFamily: 'JetBrains Mono, monospace' }}>
                  {e.event}
                </span>
                <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                  by {e.actor}
                </span>
                {e.amount && (
                  <span style={{ fontSize: 11, color: '#10b981', fontWeight: 600 }}>
                    {formatINR(e.amount)}
                  </span>
                )}
              </div>
              {e.reason && (
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 2 }}>{e.reason}</div>
              )}
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{formatTime(e.timestamp)}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Voice Agent Panel ─────────────────────────────────────────────────────────

function VoiceAgentPanel({ customer }: { customer: Customer }) {
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'error' | 'disconnecting'>('idle');
  const [micGranted, setMicGranted] = useState(false);
  const [transcript, setTranscript] = useState<string[]>([]);
  const roomRef = useRef<Room | null>(null);
  const [agentTalking, setAgentTalking] = useState(false);
  const [userTalking, setUserTalking] = useState(false);

  const startCall = async () => {
    setStatus('connecting');
    setTranscript([]);
    try {
      // 1. Request microphone permission first
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(t => t.stop()); // Just needed the permission grant
      setMicGranted(true);
      setTranscript(prev => [...prev, '🎤 Microphone: Permission granted']);

      // 2. Get LiveKit token from backend (includes URL and room name)
      const tokenData = await getLiveKitToken(customer.customer_id);
      const { token, livekit_url, room_name } = tokenData;
      setTranscript(prev => [...prev, `🔑 Token: Received for room ${room_name}`]);

      // 3. Start recovery session on backend (creates audit event)
      await startRecovery(customer.customer_id);

      // 4. Create LiveKit room and wire up events BEFORE connecting
      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      // Remote audio track subscribed → attach and play it
      room.on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
        if (track.kind === Track.Kind.Audio) {
          const audioEl = track.attach() as HTMLAudioElement;
          // Required for Chrome/Firefox autoplay policy when joining via button click
          audioEl.autoplay = true;
          audioEl.muted = false;
          audioEl.volume = 1.0;
          document.body.appendChild(audioEl);
          setTranscript(prev => [...prev, `🔊 Audio: Agent audio track received from ${participant.identity}`]);
          setAgentTalking(true);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach().forEach(el => el.remove());
        }
      });

      // Update speaking indicators
      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        const local = speakers.find(s => s.isLocal);
        const remote = speakers.find(s => !s.isLocal);
        setUserTalking(!!local);
        setAgentTalking(!!remote);
      });

      // Remote participant joined → likely the AI agent
      room.on(RoomEvent.ParticipantConnected, (participant) => {
        setTranscript(prev => [...prev, `🤖 Agent: ${participant.identity} joined the room`]);
      });

      // Room fully connected
      room.on(RoomEvent.Connected, () => {
        setTranscript(prev => [...prev, '✅ LiveKit: Connected — waiting for AI agent...']);
      });

      // Connection state changes (useful for debugging)
      room.on(RoomEvent.ConnectionStateChanged, (state) => {
        console.log('[LiveKit] Connection state:', state);
      });

      room.on(RoomEvent.Disconnected, () => {
        setStatus('idle');
        setAgentTalking(false);
        setUserTalking(false);
        setTranscript(prev => [...prev, '📴 Call ended']);
        // Clean up any lingering audio elements
        document.querySelectorAll('audio[data-lk-audio]').forEach(el => el.remove());
      });

      // 5. Connect to LiveKit room using URL from backend (never hardcoded)
      setTranscript(prev => [...prev, `📡 Connecting to LiveKit room: ${room_name}...`]);
      await room.connect(livekit_url, token, { autoSubscribe: true });

      // 6. Publish microphone track so the agent can hear us
      await room.localParticipant.setMicrophoneEnabled(true);
      setTranscript(prev => [...prev, '🎤 Microphone: Publishing audio to room']);

      // Only mark connected AFTER room.connect() resolves (RoomEvent.Connected also fires)
      setStatus('connected');

    } catch (err: any) {
      console.error('[LiveKit] Failed to start call:', err);
      setStatus('error');
      setTranscript(prev => [...prev, `❌ Error: ${err.message || 'Unknown error'}`]);
    }
  };

  const endCall = async () => {
    setStatus('disconnecting');
    if (roomRef.current) {
      // Detach all remote audio tracks before disconnecting
      roomRef.current.remoteParticipants.forEach(participant => {
        participant.audioTrackPublications.forEach(pub => {
          if (pub.track) pub.track.detach().forEach(el => el.remove());
        });
      });
      await roomRef.current.disconnect();
      roomRef.current = null;
    }
    setStatus('idle');
    setAgentTalking(false);
    setUserTalking(false);
  };

  const isConnected = status === 'connected';
  const isConnecting = status === 'connecting';
  const isError = status === 'error';

  return (
    <div className={`card ${isConnected ? 'animate-glow-pulse' : ''}`} style={{
      border: isConnected ? '1px solid rgba(99,102,241,0.4)' : undefined,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 20px', borderBottom: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
          AI Recovery Call
        </div>
        {isConnected && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%', background: '#10b981',
              animation: 'pulse-ring 2s ease-out infinite',
            }} />
            <span style={{ fontSize: 12, color: '#10b981', fontWeight: 600 }}>Connected</span>
          </div>
        )}
      </div>

      <div style={{ padding: '24px' }}>
        {/* Voice Visualization */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, marginBottom: 24,
        }}>
          {/* Waveform */}
          <div style={{
            width: 80, height: 80, borderRadius: '50%',
            background: isConnected ? 'rgba(99,102,241,0.1)' : 'var(--color-surface-2)',
            border: `2px solid ${isConnected ? 'rgba(99,102,241,0.4)' : 'var(--color-border)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.3s',
          }}>
            {isConnected ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    className="waveform-bar"
                    style={{
                      height: agentTalking ? undefined : 8,
                      animationDelay: `${i * 0.1}s`,
                      animationPlayState: agentTalking ? 'running' : 'paused',
                    }}
                  />
                ))}
              </div>
            ) : (
              <span style={{ fontSize: 28 }}>🎙️</span>
            )}
          </div>

          {/* Status text */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text)', marginBottom: 4 }}>
              {status === 'idle' && 'AI Revenue Recovery Agent'}
              {status === 'connecting' && (
                <span>Connecting<span className="dot-loading"><span/><span/><span/></span></span>
              )}
              {status === 'connected' && (agentTalking ? '🤖 Agent Speaking...' : userTalking ? '🎤 Listening...' : '● Agent Ready')}
              {status === 'disconnecting' && 'Disconnecting...'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
              {isConnected
                ? `Recovery session: ${customer.name} | ${customer.invoice_id}`
                : 'Hinglish voice recovery via LiveKit'}
            </div>
          </div>
        </div>

        {/* Call Controls */}
        {status === 'idle' && (
          <button id="start-recovery-call" className="btn-primary" onClick={startCall}
            style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', fontSize: 14 }}>
            📞 Start AI Recovery Call
          </button>
        )}
        {status === 'connecting' && (
          <button className="btn-primary" disabled style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', fontSize: 14 }}>
            Connecting...
          </button>
        )}
        {status === 'connected' && (
          <button className="btn-danger" onClick={endCall}
            style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', fontSize: 14 }}>
            ✕ End Call
          </button>
        )}
        {status === 'error' && (
          <button id="retry-recovery-call" className="btn-primary" onClick={startCall}
            style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', fontSize: 14 }}>
            ↺ Retry Connection
          </button>
        )}

        {/* Microphone tip / Error */}
        {!micGranted && status === 'idle' && (
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', textAlign: 'center', marginTop: 10 }}>
            Browser will request microphone permission when you start.
          </p>
        )}
        {isError && (
          <p style={{ fontSize: 12, color: '#ef4444', textAlign: 'center', marginTop: 10 }}>
            Connection failed. Check browser console and ensure LiveKit worker is running.
          </p>
        )}

        {/* Transcript */}
        {transcript.length > 0 && (
          <div style={{
            marginTop: 16, background: 'var(--color-surface-2)',
            borderRadius: 8, padding: '12px', maxHeight: 160, overflowY: 'auto',
          }}>
            {transcript.map((t, i) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 4, fontFamily: 'JetBrains Mono, monospace' }}>
                {t}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CustomerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const customerId = params.id as string;

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [c, e] = await Promise.all([
        fetchCustomer(customerId),
        fetchAuditTrail(customerId),
      ]);
      setCustomer(c);
      setEvents(e);
    } catch (err) {
      // customer not found
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000); // Refresh every 5s for live updates
    return () => clearInterval(interval);
  }, [load]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div className="dot-loading" style={{ gap: 8 }}>
          <span/><span/><span/>
        </div>
      </div>
    );
  }

  if (!customer) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', gap: 12 }}>
        <div style={{ fontSize: 40 }}>🔍</div>
        <div style={{ fontWeight: 600 }}>Customer not found</div>
        <button className="btn-primary" onClick={() => router.push('/')}>← Back to Dashboard</button>
      </div>
    );
  }

  const rs = customer.recovery_state;
  const decisionColor = DECISION_COLORS[rs?.current_decision || ''] || '#64748b';

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-bg)' }}>
      {/* Header */}
      <header style={{
        borderBottom: '1px solid var(--color-border)',
        padding: '16px 32px',
        display: 'flex', alignItems: 'center', gap: 16,
        background: 'rgba(17,19,24,0.95)',
        backdropFilter: 'blur(10px)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <button onClick={() => router.push('/')}
          style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '6px 12px', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: 13 }}>
          ← Dashboard
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, color: 'white', fontSize: 14,
          }}>
            {customer.name.charAt(0)}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>{customer.name}</div>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
              {customer.customer_id} · {customer.invoice_id}
            </div>
          </div>
        </div>
        {rs?.current_decision && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Policy Decision:</span>
            <span style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 700, fontSize: 13,
              color: decisionColor,
              background: `${decisionColor}15`,
              border: `1px solid ${decisionColor}30`,
              borderRadius: 6, padding: '4px 10px',
            }}>
              {rs.current_decision}
            </span>
          </div>
        )}
      </header>

      <main style={{ padding: '24px 32px', maxWidth: 1400, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 340px', gap: 20, alignItems: 'start' }}>

          {/* ── Left Column ─────────────────────────────────── */}
          <div>
            {/* Customer Info */}
            <SectionCard title="Customer Information">
              <InfoRow label="Name" value={customer.name} />
              <InfoRow label="Phone" value={customer.contact.phone} />
              <InfoRow label="Email" value={customer.contact.email} />
              <InfoRow label="Customer ID" value={<span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>{customer.customer_id}</span>} />
              <InfoRow label="Risk Level" value={
                <span className={`badge badge-${customer.risk_level === 'CRITICAL' || customer.risk_level === 'HIGH' ? 'red' : customer.risk_level === 'MEDIUM' ? 'amber' : 'green'}`}>
                  {customer.risk_level}
                </span>
              } />
            </SectionCard>

            {/* Payment Info */}
            <SectionCard title="Payment Information">
              <InfoRow label="Invoice ID" value={<span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>{customer.invoice_id}</span>} />
              <InfoRow label="Amount Due" value={<span style={{ fontSize: 16, fontWeight: 800, color: '#ef4444' }}>₹{customer.amount_due.toLocaleString('en-IN')}</span>} />
              <InfoRow label="Payment Status" value={
                <span className={`badge badge-${customer.payment_status === 'PAID' ? 'green' : 'red'}`}>
                  {customer.payment_status}
                </span>
              } />
              <InfoRow label="Failure Reason" value={customer.failure_reason} />
              <InfoRow label="Days Overdue" value={customer.days_overdue === 0 ? '—' : `${customer.days_overdue} days`}
                accent={customer.days_overdue > 7 ? '#ef4444' : undefined} />
              <InfoRow label="Previous Attempts" value={customer.previous_attempts} />
            </SectionCard>

            {/* Recovery Info */}
            <SectionCard title="Recovery Information">
              <InfoRow label="Recovery Status" value={
                <span className={`badge badge-${rs?.status === 'RECOVERED' ? 'green' : rs?.status === 'ESCALATED' ? 'red' : 'blue'}`}>
                  {rs?.status || 'NOT_STARTED'}
                </span>
              } />
              <InfoRow label="Recovery Score" value={rs?.recovery_score != null ? `${rs.recovery_score}/100` : '—'} />
              <InfoRow label="Customer Intent" value={rs?.customer_intent || '—'} />
              <InfoRow label="Verified" value={rs?.customer_verified ? '✓ Yes' : '✗ No'} accent={rs?.customer_verified ? '#10b981' : '#ef4444'} />
              <InfoRow label="Call Attempts" value={`${rs?.call_attempts || 0} / 2`} />
              <InfoRow label="Payment Links" value={`${rs?.payment_links_generated || 0} / 2`} />
              <InfoRow label="Amount Recovered" value={
                <span style={{ color: '#10b981', fontWeight: 700 }}>{formatINR(rs?.amount_recovered || 0)}</span>
              } />
              {rs?.promise_to_pay && (
                <>
                  <InfoRow label="PTP Date" value={rs.promise_to_pay.promise_date} accent="#f59e0b" />
                  <InfoRow label="PTP Amount" value={formatINR(rs.promise_to_pay.amount)} />
                  <InfoRow label="PTP Status" value={rs.promise_to_pay.fulfilled ? '✓ Fulfilled' : 'Pending'} />
                </>
              )}
              {rs?.escalated && (
                <InfoRow label="Escalation Reason" value={rs.escalation_reason || '—'} accent="#ef4444" />
              )}
            </SectionCard>

            {/* Payment Links */}
            {rs?.payment_links && rs.payment_links.length > 0 && (
              <SectionCard title="Payment Links">
                {rs.payment_links.map((link, i) => (
                  <div key={i} style={{ padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--color-text-muted)' }}>
                        {link.link_id}
                      </span>
                      <span className={`badge badge-${link.status === 'paid' ? 'green' : 'blue'}`}>{link.status}</span>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#10b981', marginBottom: 2 }}>
                      {formatINR(link.amount)}
                    </div>
                    {link.short_url && (
                      <a href={link.short_url} target="_blank" rel="noreferrer"
                        style={{ fontSize: 12, color: '#6366f1', textDecoration: 'none' }}>
                        {link.short_url} ↗
                      </a>
                    )}
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>
                      Created: {formatTime(link.created_at)}
                    </div>
                  </div>
                ))}
              </SectionCard>
            )}
          </div>

          {/* ── Center Column ─────────────────────────────── */}
          <div>
            {/* AI Decision */}
            {rs?.current_decision && (
              <div className="card" style={{ marginBottom: 16, overflow: 'hidden', border: `1px solid ${decisionColor}30` }}>
                <div style={{
                  padding: '14px 20px', borderBottom: `1px solid ${decisionColor}20`,
                  background: `${decisionColor}08`,
                  fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: decisionColor,
                }}>
                  AI Recovery Decision
                </div>
                <div style={{ padding: '20px' }}>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 4 }}>CUSTOMER</div>
                    <div style={{ fontWeight: 600 }}>{customer.name} · {formatINR(customer.amount_due)}</div>
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 4 }}>DECISION</div>
                    <div style={{
                      fontSize: 18, fontWeight: 800, color: decisionColor,
                      fontFamily: 'JetBrains Mono, monospace',
                    }}>
                      {rs.current_decision}
                    </div>
                  </div>
                  {rs.current_decision_reason && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 4 }}>REASON</div>
                      <div style={{ fontSize: 13, color: 'var(--color-text-dim)', lineHeight: 1.5 }}>
                        {rs.current_decision_reason}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Recovery Limits */}
            <SectionCard title="Recovery Policy">
              {[
                { label: 'Call Attempts', used: rs?.call_attempts || 0, max: 2 },
                { label: 'Payment Links', used: rs?.payment_links_generated || 0, max: 2 },
                { label: 'Reminders', used: rs?.reminders_sent || 0, max: 2 },
              ].map(({ label, used, max }) => (
                <div key={label} style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{label}</span>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{used} / {max}</span>
                  </div>
                  <div className="score-bar-track">
                    <div className="score-bar-fill" style={{
                      width: `${(used / max) * 100}%`,
                      background: used >= max ? '#ef4444' : used > 0 ? '#f59e0b' : '#6366f1',
                    }} />
                  </div>
                </div>
              ))}
            </SectionCard>

            {/* Recovery Score */}
            {rs?.recovery_score != null && (
              <SectionCard title="Recovery Score Breakdown">
                <ScoreBreakdown score={rs.recovery_score} breakdown={{}} />
              </SectionCard>
            )}

            {/* Audit Trail */}
            <SectionCard title={`Audit Trail (${events.length} events)`}>
              <AuditTimeline events={events} />
            </SectionCard>
          </div>

          {/* ── Right Column — Voice Agent ────────────────── */}
          <div style={{ position: 'sticky', top: 88 }}>
            <VoiceAgentPanel customer={customer} />

            {/* Quick info card */}
            <div className="card" style={{ marginTop: 16, padding: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 12 }}>
                Demo Conversation
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
                {customer.payment_status === 'PAID'
                  ? '"Maine payment already kar diya hai." → STOP_PAID'
                  : customer.amount_due > 25000
                  ? '"Payment karna hai" → ESCALATE (high value)'
                  : customer.risk_level === 'HIGH'
                  ? '"Card se payment nahi hua" → RECOVER_NOW → Payment Link'
                  : '"Kal salary aayegi, kal karunga" → TRACK_PROMISE_TO_PAY'}
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
