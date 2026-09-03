// API client for backend communication

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDashboardStats() {
  const res = await fetch(`${API_BASE}/api/dashboard/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch dashboard stats");
  return res.json();
}

export async function fetchCustomers() {
  const res = await fetch(`${API_BASE}/api/customers`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch customers");
  const data = await res.json();
  return data.customers as Customer[];
}

export async function fetchCustomer(id: string) {
  const res = await fetch(`${API_BASE}/api/customers/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Customer not found");
  return res.json() as Promise<Customer>;
}

export async function fetchAuditTrail(id: string) {
  const res = await fetch(`${API_BASE}/api/customers/${id}/audit`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch audit trail");
  const data = await res.json();
  return data.events as AuditEvent[];
}

export async function startRecovery(customerId: string) {
  const res = await fetch(`${API_BASE}/api/recovery/${customerId}/start`, {
    method: "POST",
  });
  return res.json();
}

export async function getLiveKitToken(customerId: string) {
  const res = await fetch(`${API_BASE}/api/livekit/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      customer_id: customerId,
      room_name: `recovery-${customerId}`,
      participant_name: "agent-user",
    }),
  });
  if (!res.ok) throw new Error("Failed to get LiveKit token");
  return res.json() as Promise<{ token: string; room_name: string; livekit_url: string }>;
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DashboardStats {
  revenue_at_risk: number;
  revenue_recovered: number;
  recovery_rate: number;
  active_recoveries: number;
  customers_contacted: number;
  total_customers: number;
}

export interface Customer {
  customer_id: string;
  name: string;
  contact: { phone: string; email: string };
  invoice_id: string;
  amount_due: number;
  payment_status: string;
  failure_reason: string;
  days_overdue: number;
  previous_attempts: number;
  dispute: boolean;
  risk_level: string;
  recovery_state: RecoveryState;
  created_at: string;
  updated_at: string;
}

export interface RecoveryState {
  status: string;
  call_attempts: number;
  payment_links_generated: number;
  reminders_sent: number;
  recovery_start_date: string | null;
  last_action: string | null;
  last_action_at: string | null;
  current_decision: string | null;
  current_decision_reason: string | null;
  customer_intent: string | null;
  customer_verified: boolean;
  dispute_raised: boolean;
  contact_change_requested: boolean;
  promise_to_pay: PromiseToPay | null;
  payment_links: PaymentLink[];
  amount_recovered: number;
  recovery_score: number | null;
  escalated: boolean;
  escalation_reason: string | null;
}

export interface PromiseToPay {
  promise_date: string;
  amount: number;
  recorded_at: string;
  fulfilled: boolean;
}

export interface PaymentLink {
  link_id: string;
  short_url: string;
  amount: number;
  created_at: string;
  status: string;
}

export interface AuditEvent {
  customer_id: string;
  invoice_id: string;
  event: string;
  amount: number | null;
  actor: string;
  reason: string | null;
  metadata: Record<string, string> | null;
  timestamp: string;
}
