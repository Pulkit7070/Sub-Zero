/**
 * API client for Sub-Zero backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Subscription {
  id: string;
  vendor_name: string;
  vendor_normalized: string | null;
  amount_cents: number | null;
  currency: string;
  billing_cycle: string | null;
  last_charge_at: string | null;
  next_renewal_at: string | null;
  status: string;
  source: string;
  confidence: number;
  created_at: string;
  updated_at: string;
}

export interface Decision {
  id: string;
  subscription_id: string;
  subscription: Subscription | null;
  decision_type: "cancel" | "keep" | "review" | "remind";
  reason: string | null;
  confidence: number | null;
  user_action: "accepted" | "rejected" | "snoozed" | null;
  acted_at: string | null;
  created_at: string;
}

export interface SyncResponse {
  status: string;
  subscriptions_found: number;
  new_subscriptions: number;
  updated_subscriptions: number;
  emails_processed: number;
  emails_skipped: number;
  is_incremental: boolean;
  sync_from_date: string | null;
  message: string | null;
}

export interface DecisionStats {
  pending_decisions: number;
  accepted_decisions: number;
  potential_savings_cents: number;
  actual_savings_cents: number;
}

export interface WasteEquivalent {
  label: string;
  value: number;
  emoji: string;
}

export interface WasteStats {
  annual_total_cents: number;
  monthly_avg_cents: number;
  waste_score: number;
  potentially_wasted_cents: number;
  equivalents: WasteEquivalent[];
  shock_stat: string;
}

export interface PriceChange {
  subscription_id: string;
  vendor_name: string;
  old_amount_cents: number;
  new_amount_cents: number;
  change_percent: number;
  detected_at: string;
}

export interface TrialAlert {
  subscription_id: string;
  vendor_name: string;
  trial_started_at: string;
  days_remaining: number;
  is_urgent: boolean;
  estimated_charge_cents: number;
}

export interface OverlapGroup {
  category: string;
  subscriptions: Array<{
    id: string;
    vendor_name: string;
    amount_cents: number;
    billing_cycle: string;
  }>;
  combined_monthly_cents: number;
  potential_savings_cents: number;
}

export interface NonUsePrediction {
  subscription_id: string;
  vendor_name: string;
  probability: number;
  risk_level: "low" | "medium" | "high";
  reason: string;
  days_inactive: number;
  amount_cents: number;
}

export interface IntelligenceStats {
  waste_stats: WasteStats;
  price_changes: PriceChange[];
  trial_alerts: TrialAlert[];
  overlaps: OverlapGroup[];
  non_use_predictions: NonUsePrediction[];
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(response.status, error.detail || "Request failed");
  }

  return response;
}

export const api = {
  // Auth
  getLoginUrl: () => `${API_URL}/auth/google/login`,

  getCurrentUser: async (): Promise<User> => {
    const response = await fetchWithAuth("/auth/me");
    return response.json();
  },

  logout: async (): Promise<void> => {
    await fetchWithAuth("/auth/logout", { method: "POST" });
  },

  // Subscriptions
  getSubscriptions: async (status?: string): Promise<Subscription[]> => {
    const params = status ? `?status_filter=${status}` : "";
    const response = await fetchWithAuth(`/subscriptions${params}`);
    return response.json();
  },

  syncSubscriptions: async (daysBack: number = 365, force: boolean = false): Promise<SyncResponse> => {
    const response = await fetchWithAuth("/subscriptions/sync", {
      method: "POST",
      body: JSON.stringify({ days_back: daysBack, force }),
    });
    return response.json();
  },

  deleteSubscription: async (id: string): Promise<void> => {
    await fetchWithAuth(`/subscriptions/${id}`, { method: "DELETE" });
  },

  // Decisions
  getDecisions: async (pendingOnly: boolean = true): Promise<Decision[]> => {
    const params = `?pending_only=${pendingOnly}`;
    const response = await fetchWithAuth(`/decisions${params}`);
    return response.json();
  },

  generateDecisions: async (): Promise<{
    status: string;
    decisions_generated: number;
    potential_savings_cents: number;
    message: string;
  }> => {
    const response = await fetchWithAuth("/decisions/generate", { method: "POST" });
    return response.json();
  },

  actOnDecision: async (
    id: string,
    action: "accepted" | "rejected" | "snoozed"
  ): Promise<{ status: string; message: string }> => {
    const response = await fetchWithAuth(`/decisions/${id}/act`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    return response.json();
  },

  getDecisionStats: async (): Promise<DecisionStats> => {
    const response = await fetchWithAuth("/decisions/summary/stats");
    return response.json();
  },

  // Intelligence
  getIntelligenceStats: async (): Promise<IntelligenceStats> => {
    const response = await fetchWithAuth("/intelligence/stats");
    return response.json();
  },

  // LLM
  generateRiskExplanation: async (probability: number, reasons: string[]): Promise<string> => {
    const response = await fetchWithAuth("/llm/risk-explain", {
      method: "POST",
      body: JSON.stringify({ probability, reasons }),
    });
    const data = await response.json();
    return data.text;
  },

  generateFinalSummary: async (savings: number, count: number, alertsAvoided: number): Promise<string> => {
    const response = await fetchWithAuth("/llm/final-summary", {
      method: "POST",
      body: JSON.stringify({ savings, count, alerts_avoided: alertsAvoided }),
    });
    const data = await response.json();
    return data.text;
  },
};

export function formatCurrency(cents: number | null, currency: string = "USD"): string {
  if (cents === null) return "—";
  const amount = cents / 100;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount);
}

export function formatDate(dateString: string | null): string {
  if (!dateString) return "—";
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatRelativeDate(dateString: string | null): string {
  if (!dateString) return "—";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}
