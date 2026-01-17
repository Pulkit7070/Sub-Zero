"use client";

import { useEffect, useState } from "react";
import EnterpriseLayout from "@/components/EnterpriseLayout";
import {
  CreditCard,
  Search,
  Filter,
  Calendar,
  AlertTriangle,
  TrendingDown,
  Users,
  Clock,
  ChevronDown,
  MoreVertical,
} from "lucide-react";
import {
  subscriptionsAPI,
  ToolSubscription,
  formatCurrency,
  formatPercent,
} from "@/lib/enterprise-api";
import { useDemoData } from "@/lib/demo-data";

const ORG_ID = "demo-org-id";
const USE_DEMO_DATA = true;

export default function SubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<ToolSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [renewalFilter, setRenewalFilter] = useState<number | null>(null);
  const [spendSummary, setSpendSummary] = useState<any>(null);
  const [upcomingRenewals, setUpcomingRenewals] = useState<any[]>([]);

  useEffect(() => {
    loadData();
  }, [statusFilter, renewalFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      if (USE_DEMO_DATA) {
        const demoData = useDemoData();
        let filteredSubs = demoData.subscriptions;
        
        if (statusFilter !== "all") {
          filteredSubs = filteredSubs.filter(s => s.status === statusFilter);
        }
        if (renewalFilter) {
          filteredSubs = filteredSubs.filter(s => 
            s.days_until_renewal && s.days_until_renewal <= renewalFilter
          );
        }
        
        setSubscriptions(filteredSubs);
        
        // Calculate spend summary from demo data
        const totalMonthly = demoData.subscriptions.reduce((sum, s) => 
          sum + (s.amount_cents || 0) / (s.billing_cycle === "annual" ? 12 : 1), 0
        );
        const totalAnnual = demoData.subscriptions.reduce((sum, s) => 
          sum + (s.amount_cents || 0) * (s.billing_cycle === "monthly" ? 12 : 1), 0
        );
        
        setSpendSummary({
          total_monthly_cents: totalMonthly,
          total_annual_cents: totalAnnual,
          by_category: {},
          by_department: {}
        });
        
        // Upcoming renewals
        const upcoming = demoData.subscriptions
          .filter(s => s.days_until_renewal && s.days_until_renewal <= 60)
          .sort((a, b) => (a.days_until_renewal || 0) - (b.days_until_renewal || 0));
        setUpcomingRenewals(upcoming);
        
        setLoading(false);
        return;
      }
      
      const params: any = { page_size: 100 };
      if (statusFilter !== "all") params.status = statusFilter;
      if (renewalFilter) params.renewal_within_days = renewalFilter;

      const [subsResponse, spendResponse, renewalsResponse] = await Promise.all([
        subscriptionsAPI.list(ORG_ID, params),
        subscriptionsAPI.getSpendSummary(ORG_ID).catch(() => null),
        subscriptionsAPI.getUpcomingRenewals(ORG_ID, 60).catch(() => ({ renewals: [] })),
      ]);

      setSubscriptions(subsResponse.items);
      setSpendSummary(spendResponse);
      setUpcomingRenewals(renewalsResponse.renewals);
    } catch (error) {
      console.error("Failed to load subscriptions:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredSubs = subscriptions.filter((sub) =>
    sub.tool_name?.toLowerCase().includes(search.toLowerCase()) ||
    sub.department?.toLowerCase().includes(search.toLowerCase())
  );

  const getUtilizationColor = (rate: number) => {
    if (rate >= 0.7) return "text-green-600 bg-green-100";
    if (rate >= 0.5) return "text-amber-600 bg-amber-100";
    if (rate >= 0.3) return "text-orange-600 bg-orange-100";
    return "text-red-600 bg-red-100";
  };

  const getRenewalUrgency = (days: number | null | undefined) => {
    if (!days) return null;
    if (days <= 7) return { text: "Urgent", color: "bg-red-100 text-red-700" };
    if (days <= 30) return { text: "Soon", color: "bg-amber-100 text-amber-700" };
    if (days <= 60) return { text: "Upcoming", color: "bg-blue-100 text-blue-700" };
    return null;
  };

  return (
    <EnterpriseLayout>
      <div className="space-y-6">
        {/* Demo Banner */}
        {USE_DEMO_DATA && (
          <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
                <CreditCard className="w-5 h-5 text-green-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">
                  Demo: Subscription Management
                </h3>
                <p className="text-sm text-gray-600">
                  View all company subscriptions with real-time utilization tracking, renewal alerts, 
                  and automated optimization suggestions. Demo showing Slack, Figma, Zoom, GitHub, and Notion.
                </p>
              </div>
            </div>
          </div>
        )}
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Subscriptions</h1>
            <p className="text-gray-500">
              Manage your SaaS subscriptions and renewals
            </p>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Monthly Spend</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(spendSummary?.total_monthly_cents || 0)}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-xl">
                <CreditCard className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Annual Spend</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(spendSummary?.total_annual_cents || 0)}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-xl">
                <TrendingDown className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Active Subscriptions</p>
                <p className="text-2xl font-bold text-gray-900">
                  {subscriptions.filter((s) => s.status === "active").length}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-xl">
                <CreditCard className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Renewals (60 days)</p>
                <p className="text-2xl font-bold text-gray-900">
                  {upcomingRenewals.length}
                </p>
              </div>
              <div className="p-3 bg-amber-100 rounded-xl">
                <Calendar className="w-6 h-6 text-amber-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Upcoming Renewals Alert */}
        {upcomingRenewals.filter((r) => r.urgency === "urgent").length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <div>
                <p className="font-medium text-red-800">
                  {upcomingRenewals.filter((r) => r.urgency === "urgent").length}{" "}
                  subscriptions renewing within 7 days
                </p>
                <p className="text-sm text-red-600">
                  Review these before renewal to avoid unwanted charges
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search subscriptions..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-3">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="cancelled">Cancelled</option>
                <option value="expired">Expired</option>
              </select>
              <select
                value={renewalFilter || ""}
                onChange={(e) =>
                  setRenewalFilter(e.target.value ? parseInt(e.target.value) : null)
                }
                className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Renewals</option>
                <option value="7">Within 7 days</option>
                <option value="30">Within 30 days</option>
                <option value="60">Within 60 days</option>
                <option value="90">Within 90 days</option>
              </select>
            </div>
          </div>
        </div>

        {/* Subscriptions Table */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : filteredSubs.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <CreditCard className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No subscriptions found
            </h3>
            <p className="text-gray-500">
              {search || statusFilter !== "all"
                ? "Try adjusting your filters"
                : "Add subscriptions to your tools to track them"}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Tool
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Utilization
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Owner
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Renewal
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredSubs.map((sub) => {
                  const urgency = getRenewalUrgency(sub.days_until_renewal);
                  const utilization = sub.utilization_rate || 0;

                  return (
                    <tr key={sub.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-900">
                            {sub.tool_name || "Unknown Tool"}
                          </p>
                          <p className="text-sm text-gray-500">
                            {sub.plan_name || sub.billing_cycle}
                          </p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <p className="font-medium text-gray-900">
                          {formatCurrency(sub.amount_cents || 0)}
                        </p>
                        <p className="text-sm text-gray-500">
                          /{sub.billing_cycle}
                        </p>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${getUtilizationColor(
                              utilization
                            )}`}
                          >
                            {formatPercent(utilization)}
                          </span>
                          <span className="text-sm text-gray-500">
                            {sub.active_seats}/{sub.paid_seats} seats
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {sub.owner_name ? (
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center text-xs font-medium">
                              {sub.owner_name.charAt(0)}
                            </div>
                            <span className="text-sm text-gray-900">
                              {sub.owner_name}
                            </span>
                            {sub.owner_status === "offboarded" && (
                              <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs rounded">
                                Left
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">Unassigned</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {sub.renewal_date ? (
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-900">
                              {new Date(sub.renewal_date).toLocaleDateString()}
                            </span>
                            {urgency && (
                              <span
                                className={`px-2 py-0.5 rounded text-xs font-medium ${urgency.color}`}
                              >
                                {urgency.text}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            sub.status === "active"
                              ? "bg-green-100 text-green-700"
                              : sub.status === "cancelled"
                              ? "bg-red-100 text-red-700"
                              : "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {sub.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <button className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400">
                          <MoreVertical className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </EnterpriseLayout>
  );
}
