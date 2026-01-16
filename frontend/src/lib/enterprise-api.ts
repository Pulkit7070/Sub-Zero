/**
 * Enterprise API Client
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface Organization {
  id: string;
  name: string;
  domain: string;
  plan: string;
  settings: Record<string, any>;
  sso_provider?: string;
  created_at: string;
  updated_at: string;
}

export interface OrgUser {
  id: string;
  org_id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  department?: string;
  job_title?: string;
  role: string;
  manager_id?: string;
  status: string;
  last_login_at?: string;
  created_at: string;
}

export interface SaaSTool {
  id: string;
  org_id: string;
  name: string;
  normalized_name: string;
  category?: string;
  vendor_domain?: string;
  logo_url?: string;
  description?: string;
  status: string;
  is_keystone: boolean;
  keystone_score: number;
  created_at: string;
  // Extended stats
  active_users?: number;
  total_users?: number;
  monthly_cost?: number;
  dependency_count?: number;
}

export interface ToolSubscription {
  id: string;
  org_id: string;
  tool_id: string;
  plan_name?: string;
  billing_cycle: string;
  amount_cents?: number;
  currency: string;
  paid_seats?: number;
  active_seats: number;
  renewal_date?: string;
  auto_renew: boolean;
  owner_id?: string;
  department?: string;
  status: string;
  created_at: string;
  // Joined fields
  tool_name?: string;
  owner_name?: string;
  owner_status?: string;
  utilization_rate?: number;
  days_until_renewal?: number;
}

export interface Decision {
  id: string;
  org_id: string;
  subscription_id?: string;
  tool_id?: string;
  decision_type: string;
  confidence: number;
  risk_score: number;
  savings_potential_cents: number;
  recommended_seats?: number;
  explanation?: string;
  factors?: any[];
  status: string;
  priority: string;
  due_date?: string;
  created_at: string;
  // Joined
  tool_name?: string;
}

export interface DashboardStats {
  total_tools: number;
  active_subscriptions: number;
  total_users: number;
  monthly_spend_cents: number;
  annual_spend_cents: number;
  potential_savings_cents: number;
  pending_decisions: number;
  tools_under_review: number;
  avg_utilization: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Helper
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// Organizations
export const organizationsAPI = {
  create: (data: { name: string; domain: string }) =>
    fetchAPI<Organization>("/api/v1/organizations", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  list: (params?: { page?: number; search?: string }) =>
    fetchAPI<PaginatedResponse<Organization>>(
      `/api/v1/organizations?${new URLSearchParams(params as any)}`
    ),

  get: (orgId: string) =>
    fetchAPI<Organization>(`/api/v1/organizations/${orgId}`),

  getByDomain: (domain: string) =>
    fetchAPI<Organization>(`/api/v1/organizations/by-domain/${domain}`),

  update: (orgId: string, data: Partial<Organization>) =>
    fetchAPI<Organization>(`/api/v1/organizations/${orgId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

// Users
export const usersAPI = {
  list: (orgId: string, params?: { page?: number; search?: string; department?: string; status?: string }) =>
    fetchAPI<PaginatedResponse<OrgUser>>(
      `/api/v1/organizations/${orgId}/users?${new URLSearchParams(params as any)}`
    ),

  get: (orgId: string, userId: string) =>
    fetchAPI<OrgUser>(`/api/v1/organizations/${orgId}/users/${userId}`),

  create: (orgId: string, data: Partial<OrgUser>) =>
    fetchAPI<OrgUser>(`/api/v1/organizations/${orgId}/users`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (orgId: string, userId: string, data: Partial<OrgUser>) =>
    fetchAPI<OrgUser>(`/api/v1/organizations/${orgId}/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  offboard: (orgId: string, userId: string, revokeAccess = true) =>
    fetchAPI(`/api/v1/organizations/${orgId}/users/${userId}/offboard?revoke_access=${revokeAccess}`, {
      method: "POST",
    }),

  getDepartments: (orgId: string) =>
    fetchAPI<{ departments: string[] }>(`/api/v1/organizations/${orgId}/users/departments`),
};

// Tools
export const toolsAPI = {
  list: (orgId: string, params?: { page?: number; search?: string; category?: string; status?: string }) =>
    fetchAPI<PaginatedResponse<SaaSTool>>(
      `/api/v1/organizations/${orgId}/tools?${new URLSearchParams(params as any)}`
    ),

  get: (orgId: string, toolId: string) =>
    fetchAPI<SaaSTool>(`/api/v1/organizations/${orgId}/tools/${toolId}`),

  create: (orgId: string, data: Partial<SaaSTool>) =>
    fetchAPI<SaaSTool>(`/api/v1/organizations/${orgId}/tools`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (orgId: string, toolId: string, data: Partial<SaaSTool>) =>
    fetchAPI<SaaSTool>(`/api/v1/organizations/${orgId}/tools/${toolId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (orgId: string, toolId: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/tools/${toolId}`, { method: "DELETE" }),

  getCategories: (orgId: string) =>
    fetchAPI<{ categories: Record<string, number> }>(`/api/v1/organizations/${orgId}/tools/categories`),

  getAccess: (orgId: string, toolId: string) =>
    fetchAPI<{ access: any[] }>(`/api/v1/organizations/${orgId}/tools/${toolId}/access`),

  getDependencies: (orgId: string, toolId: string) =>
    fetchAPI<{ depends_on: any[]; depended_by: any[]; keystone_score: number }>(
      `/api/v1/organizations/${orgId}/tools/${toolId}/dependencies`
    ),
};

// Subscriptions
export const subscriptionsAPI = {
  list: (orgId: string, params?: { page?: number; status?: string; department?: string; renewal_within_days?: number }) =>
    fetchAPI<PaginatedResponse<ToolSubscription>>(
      `/api/v1/organizations/${orgId}/subscriptions?${new URLSearchParams(params as any)}`
    ),

  get: (orgId: string, subId: string) =>
    fetchAPI<ToolSubscription>(`/api/v1/organizations/${orgId}/subscriptions/${subId}`),

  create: (orgId: string, data: Partial<ToolSubscription>) =>
    fetchAPI<ToolSubscription>(`/api/v1/organizations/${orgId}/subscriptions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (orgId: string, subId: string, data: Partial<ToolSubscription>) =>
    fetchAPI<ToolSubscription>(`/api/v1/organizations/${orgId}/subscriptions/${subId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  cancel: (orgId: string, subId: string, reason?: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/subscriptions/${subId}/cancel?reason=${reason || ""}`, {
      method: "POST",
    }),

  getUpcomingRenewals: (orgId: string, days = 30) =>
    fetchAPI<{ renewals: any[] }>(`/api/v1/organizations/${orgId}/subscriptions/upcoming-renewals?days=${days}`),

  getSpendSummary: (orgId: string) =>
    fetchAPI<{
      total_monthly_cents: number;
      total_annual_cents: number;
      by_category: Record<string, { amount_cents: number; count: number }>;
      by_department: Record<string, { amount_cents: number; count: number }>;
    }>(`/api/v1/organizations/${orgId}/subscriptions/spend-summary`),
};

// Decisions
export const decisionsAPI = {
  list: (orgId: string, params?: { page?: number; status?: string; decision_type?: string; priority?: string }) =>
    fetchAPI<PaginatedResponse<Decision>>(
      `/api/v1/organizations/${orgId}/decisions?${new URLSearchParams(params as any)}`
    ),

  get: (orgId: string, decisionId: string) =>
    fetchAPI<Decision>(`/api/v1/organizations/${orgId}/decisions/${decisionId}`),

  getPending: (orgId: string) =>
    fetchAPI<{
      total_pending: number;
      total_potential_savings_cents: number;
      by_priority: Record<string, Decision[]>;
    }>(`/api/v1/organizations/${orgId}/decisions/pending`),

  analyze: (orgId: string, subId: string) =>
    fetchAPI<{ subscription_id: string; tool_name: string; decision: any }>(
      `/api/v1/organizations/${orgId}/decisions/analyze/${subId}`,
      { method: "POST" }
    ),

  analyzeAll: (orgId: string) =>
    fetchAPI<{ message: string; decisions_created: number; results: any[] }>(
      `/api/v1/organizations/${orgId}/decisions/analyze-all`,
      { method: "POST" }
    ),

  approve: (orgId: string, decisionId: string, approvedBy: string, notes?: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/decisions/${decisionId}/approve?approved_by=${approvedBy}&notes=${notes || ""}`, {
      method: "POST",
    }),

  reject: (orgId: string, decisionId: string, rejectedBy: string, reason?: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/decisions/${decisionId}/reject?rejected_by=${rejectedBy}&reason=${reason || ""}`, {
      method: "POST",
    }),

  execute: (orgId: string, decisionId: string, notes?: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/decisions/${decisionId}/execute?notes=${notes || ""}`, {
      method: "POST",
    }),
};

// Dashboard
export const dashboardAPI = {
  getStats: (orgId: string) =>
    fetchAPI<DashboardStats>(`/api/v1/organizations/${orgId}/dashboard/stats`),

  getSpendTrends: (orgId: string, months = 6) =>
    fetchAPI<{ trends: any[]; current_monthly_spend: number }>(
      `/api/v1/organizations/${orgId}/dashboard/spend-trends?months=${months}`
    ),

  getCategoryBreakdown: (orgId: string) =>
    fetchAPI<{ categories: Record<string, { monthly_spend_cents: number; tool_count: number }> }>(
      `/api/v1/organizations/${orgId}/dashboard/category-breakdown`
    ),

  getUtilizationReport: (orgId: string) =>
    fetchAPI<{
      report: Record<string, any[]>;
      summary: {
        healthy_count: number;
        moderate_count: number;
        underutilized_count: number;
        critical_count: number;
        total_monthly_waste_cents: number;
        total_annual_waste_cents: number;
      };
    }>(`/api/v1/organizations/${orgId}/dashboard/utilization-report`),

  getRenewalCalendar: (orgId: string, days = 90) =>
    fetchAPI<{ calendar: Record<string, { renewals: any[]; total_cents: number }> }>(
      `/api/v1/organizations/${orgId}/dashboard/renewal-calendar?days=${days}`
    ),

  getQuickWins: (orgId: string) =>
    fetchAPI<{ quick_wins: any[]; total_count: number }>(
      `/api/v1/organizations/${orgId}/dashboard/quick-wins`
    ),

  getOwnerReport: (orgId: string) =>
    fetchAPI<{
      by_owner: any[];
      orphaned_subscriptions: any[];
      departed_owner_subscriptions: any[];
    }>(`/api/v1/organizations/${orgId}/dashboard/owner-report`),
};

// Integrations
export const integrationsAPI = {
  list: (orgId: string) =>
    fetchAPI<{ integrations: any[] }>(`/api/v1/organizations/${orgId}/integrations`),

  getAvailable: () =>
    fetchAPI<{ providers: any[] }>(`/api/v1/organizations/test/integrations/available`),

  connect: (orgId: string, provider: string, accessToken: string, refreshToken?: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/integrations`, {
      method: "POST",
      body: JSON.stringify({ provider, access_token: accessToken, refresh_token: refreshToken }),
    }),

  disconnect: (orgId: string, integrationId: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/integrations/${integrationId}`, { method: "DELETE" }),

  sync: (orgId: string, integrationId: string) =>
    fetchAPI(`/api/v1/organizations/${orgId}/integrations/${integrationId}/sync`, { method: "POST" }),

  getSSOConfig: (orgId: string) =>
    fetchAPI<{ sso_enabled: boolean; provider?: string; config: any }>(
      `/api/v1/organizations/${orgId}/integrations/sso/config`
    ),

  configureSSO: (orgId: string, provider: string, config: any) =>
    fetchAPI(`/api/v1/organizations/${orgId}/integrations/sso/config`, {
      method: "POST",
      body: JSON.stringify({ provider, config }),
    }),
};

// Utility
export function formatCurrency(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
