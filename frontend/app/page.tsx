'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { fetchDashboardStats, fetchCustomers, Customer, DashboardStats } from '@/lib/api';

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatINR(amount: number) {
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000)   return `₹${(amount / 1000).toFixed(1)}K`;
  return `₹${amount.toFixed(0)}`;
}

function getRiskBadge(risk: string) {
  const map: Record<string, string> = {
    CRITICAL: 'badge-red',
    HIGH:     'badge-amber',
    MEDIUM:   'badge-blue',
    LOW:      'badge-green',
  };
  return map[risk] || 'badge-gray';
}

function getStatusBadge(status: string) {
  const map: Record<string, string> = {
    RECOVERED:            'badge-green',
    STOPPED_PAID:         'badge-green',
    IN_PROGRESS:          'badge-blue',
    CALLING:              'badge-purple',
    PROMISE_TO_PAY:       'badge-amber',
    ESCALATED:            'badge-red',
    NOT_STARTED:          'badge-gray',
    STOPPED_MAX_ATTEMPTS: 'badge-red',
    STOPPED_WINDOW_EXPIRED:'badge-red',
    REFUSED:              'badge-gray',
  };
  return map[status] || 'badge-gray';
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    RECOVERED:             '✓ Recovered',
    STOPPED_PAID:          '✓ Already Paid',
    IN_PROGRESS:           'In Progress',
    CALLING:               'Calling',
    PROMISE_TO_PAY:        'Promise to Pay',
    ESCALATED:             '↑ Escalated',
    NOT_STARTED:           'Not Started',
    STOPPED_MAX_ATTEMPTS:  'Stopped (Max)',
    STOPPED_WINDOW_EXPIRED:'Stopped (Expired)',
    REFUSED:               'Refused',
  };
  return map[status] || status;
}

function getFailureLabel(reason: string) {
  const map: Record<string, string> = {
    CARD_DECLINED:               'Card Declined',
    INSUFFICIENT_FUNDS:          'Insufficient Funds',
    PAYMENT_METHOD_FAILED:       'Payment Method Failed',
    CHECKOUT_ABANDONED:          'Checkout Abandoned',
    SUBSCRIPTION_PAYMENT_FAILED: 'Subscription Failed',
    NETWORK_ERROR:               'Network Error',
    BANK_DECLINED:               'Bank Declined',
    NONE:                        '—',
  };
  return map[reason] || reason;
}

// ── Metric Card ───────────────────────────────────────────────────────────────

function MetricCard({
  label, value, sub, accent, icon,
}: { label: string; value: string; sub?: string; accent?: string; icon: string }) {
  return (
    <div className="metric-card animate-slide-up">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontSize: 24 }}>{icon}</span>
        {sub && (
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {sub}
          </span>
        )}
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color: accent || 'var(--color-text)', marginBottom: 4 }}>
        {value}
      </div>
      <div style={{ fontSize: 13, color: 'var(--color-text-muted)', fontWeight: 500 }}>{label}</div>
    </div>
  );
}

// ── Live Status Dot ───────────────────────────────────────────────────────────

function LiveDot() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%', background: '#10b981',
        boxShadow: '0 0 0 0 rgba(16,185,129,0.5)',
        animation: 'pulse-ring 2s ease-out infinite',
        display: 'inline-block',
      }} />
      <span style={{ fontSize: 12, color: '#10b981', fontWeight: 600 }}>Live</span>
    </span>
  );
}

// ── Customer Row ──────────────────────────────────────────────────────────────

function CustomerRow({ customer }: { customer: Customer }) {
  const rs = customer.recovery_state;
  return (
    <Link href={`/customers/${customer.customer_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div
        className="table-row"
        style={{ gridTemplateColumns: '2fr 1.2fr 1.8fr 1fr 1fr 1.5fr 1.5fr', gap: 12 }}
      >
        {/* Customer */}
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text)' }}>{customer.name}</div>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>{customer.customer_id}</div>
        </div>

        {/* Amount */}
        <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--color-text)' }}>
          ₹{customer.amount_due.toLocaleString('en-IN')}
        </div>

        {/* Issue */}
        <div style={{ fontSize: 13, color: 'var(--color-text-dim)' }}>
          {getFailureLabel(customer.failure_reason)}
        </div>

        {/* Risk */}
        <div>
          <span className={`badge ${getRiskBadge(customer.risk_level)}`}>
            {customer.risk_level}
          </span>
        </div>

        {/* Days Overdue */}
        <div style={{ fontSize: 13, color: customer.days_overdue > 7 ? '#ef4444' : 'var(--color-text-dim)' }}>
          {customer.days_overdue === 0 ? '—' : `${customer.days_overdue}d`}
        </div>

        {/* Recovery Status */}
        <div>
          <span className={`badge ${getStatusBadge(rs?.status || 'NOT_STARTED')}`}>
            {getStatusLabel(rs?.status || 'NOT_STARTED')}
          </span>
        </div>

        {/* Last Action */}
        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
          {rs?.call_attempts != null ? `Attempt ${rs.call_attempts}/${2}` : '—'}
          {rs?.current_decision && (
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>
              {rs.current_decision}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const load = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([fetchDashboardStats(), fetchCustomers()]);
      setStats(s);
      setCustomers(c);
      setLastRefresh(new Date());
      setError(null);
    } catch (e) {
      setError('Cannot connect to backend. Make sure the server is running on port 8000.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000); // Auto-refresh every 10s
    return () => clearInterval(interval);
  }, [load]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-bg)' }}>
      {/* ── Header ──────────────────────────────────────────────── */}
      <header style={{
        borderBottom: '1px solid var(--color-border)',
        padding: '16px 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(17,19,24,0.95)',
        backdropFilter: 'blur(10px)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18,
            }}>🎯</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--color-text)' }}>
                AI Revenue Recovery
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                Razorpay Track 03
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <LiveDot />
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Last updated: {lastRefresh.toLocaleTimeString()}
          </div>
          <button className="btn-primary" onClick={load} style={{ fontSize: 13, padding: '8px 16px' }}>
            ↻ Refresh
          </button>
        </div>
      </header>

      <main style={{ padding: '32px', maxWidth: 1400, margin: '0 auto' }}>

        {/* ── Error Banner ─────────────────────────────────────── */}
        {error && (
          <div style={{
            background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 10, padding: '14px 20px', marginBottom: 24,
            color: '#ef4444', fontSize: 14, display: 'flex', alignItems: 'center', gap: 10,
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* ── Page Title ─────────────────────────────────────────── */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--color-text)', marginBottom: 6 }}>
            Revenue Recovery Dashboard
          </h1>
          <p style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>
            AI agent detecting revenue at risk, determining interventions, and executing bounded recovery workflows.
          </p>
        </div>

        {/* ── Metrics Grid ──────────────────────────────────────── */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 16, marginBottom: 32,
        }}>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="metric-card shimmer" style={{ height: 110 }} />
            ))
          ) : stats ? (
            <>
              <MetricCard
                icon="🔥"
                label="Revenue At Risk"
                value={`₹${stats.revenue_at_risk.toLocaleString('en-IN')}`}
                accent="#ef4444"
              />
              <MetricCard
                icon="💰"
                label="Revenue Recovered"
                value={`₹${stats.revenue_recovered.toLocaleString('en-IN')}`}
                accent="#10b981"
              />
              <MetricCard
                icon="📈"
                label="Recovery Rate"
                value={`${stats.recovery_rate}%`}
                accent="#6366f1"
              />
              <MetricCard
                icon="🤖"
                label="Active Recoveries"
                value={stats.active_recoveries.toString()}
                accent="#f59e0b"
              />
              <MetricCard
                icon="📞"
                label="Customers Contacted"
                value={stats.customers_contacted.toString()}
                sub={`of ${stats.total_customers} total`}
              />
            </>
          ) : null}
        </div>

        {/* ── Customer Table ──────────────────────────────────────── */}
        <div className="card" style={{ overflow: 'hidden' }}>
          {/* Table Header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '20px 20px 16px',
            borderBottom: '1px solid var(--color-border)',
          }}>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text)' }}>
                Recovery Queue
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 2 }}>
                Click any customer to view details and start AI recovery call
              </p>
            </div>
            <span className="badge badge-purple">{customers.length} customers</span>
          </div>

          {/* Column Headers */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1.2fr 1.8fr 1fr 1fr 1.5fr 1.5fr',
            gap: 12, padding: '10px 20px',
            background: 'var(--color-surface-2)',
          }}>
            {['Customer', 'Amount Due', 'Issue', 'Risk', 'Overdue', 'Status', 'Last Action'].map(h => (
              <div key={h} style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {h}
              </div>
            ))}
          </div>

          {/* Rows */}
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="table-row shimmer" style={{ height: 60, gridTemplateColumns: '1fr' }} />
            ))
          ) : customers.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🌱</div>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>No customers found</div>
              <div style={{ fontSize: 13 }}>Run the seed script: <code style={{ fontFamily: 'JetBrains Mono, monospace', background: 'var(--color-surface-2)', padding: '2px 6px', borderRadius: 4 }}>python backend/scripts/seed_customers.py</code></div>
            </div>
          ) : (
            customers.map(c => <CustomerRow key={c.customer_id} customer={c} />)
          )}
        </div>

        {/* ── Architecture Note ─────────────────────────────────── */}
        <div style={{
          marginTop: 32, padding: '20px 24px',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 12,
        }}>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            System Architecture
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {[
              ['LiveKit', 'Voice / Realtime', '#6366f1'],
              ['LLM (Gemini)', 'NL Understanding', '#8b5cf6'],
              ['Policy Engine', 'Deterministic Authority', '#f59e0b'],
              ['MongoDB', 'Customer + State', '#10b981'],
              ['Razorpay', 'Payment Execution', '#3b82f6'],
              ['Webhook', 'Payment Truth', '#ef4444'],
            ].map(([name, role, color], i) => (
              <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{
                  background: `${color}20`, border: `1px solid ${color}40`,
                  borderRadius: 6, padding: '6px 12px',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color }}>{name}</div>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{role}</div>
                </div>
                {i < 5 && <span style={{ color: 'var(--color-border-light)', fontSize: 16 }}>→</span>}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
