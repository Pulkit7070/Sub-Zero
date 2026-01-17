"use client";

import { useEffect, useState } from "react";
import EnterpriseLayout from "@/components/EnterpriseLayout";
import {
  Package,
  CreditCard,
  Users,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
  Zap,
  DollarSign,
  PieChart,
  Calendar,
} from "lucide-react";
import Link from "next/link";
import {
  dashboardAPI,
  decisionsAPI,
  DashboardStats,
  formatCurrency,
  formatPercent,
} from "@/lib/enterprise-api";
import { useDemoData } from "@/lib/demo-data";

// Demo org ID - in real app, get from auth context
const ORG_ID = "demo-org-id";
const USE_DEMO_DATA = true; // Set to false when backend is ready

interface QuickWin {
  type: string;
  subscription_id?: string;
  tool_name?: string;
  potential_annual_savings_cents?: number;
  action: string;
  priority: string;
  category?: string;
  tool_count?: number;
}

interface UtilizationSummary {
  healthy_count: number;
  moderate_count: number;
  underutilized_count: number;
  critical_count: number;
  total_monthly_waste_cents: number;
}

export default function EnterpriseDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [quickWins, setQuickWins] = useState<QuickWin[]>([]);
  const [utilization, setUtilization] = useState<UtilizationSummary | null>(null);
  const [categorySpend, setCategorySpend] = useState<Record<string, { monthly_spend_cents: number; tool_count: number }>>({});
  const [loading, setLoading] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);

      if (USE_DEMO_DATA) {
        // Use demo data
        const demoData = useDemoData();
        setStats(demoData.stats);
        setQuickWins(demoData.quickWins as any);
        setUtilization(demoData.utilizationSummary);
        
        // Create category breakdown from demo subscriptions
        const categoryBreakdown: Record<string, { monthly_spend_cents: number; tool_count: number }> = {};
        demoData.tools.forEach(tool => {
          const category = tool.category || "Other";
          if (!categoryBreakdown[category]) {
            categoryBreakdown[category] = { monthly_spend_cents: 0, tool_count: 0 };
          }
          categoryBreakdown[category].monthly_spend_cents += (tool.monthly_cost || 0) * 100;
          categoryBreakdown[category].tool_count += 1;
        });
        setCategorySpend(categoryBreakdown);
        setPendingCount(demoData.decisions.length);
        
        setLoading(false);
        return;
      }

      // Load all dashboard data in parallel
      const [statsData, quickWinsData, utilizationData, categoryData, pendingData] = await Promise.all([
        dashboardAPI.getStats(ORG_ID).catch(() => null),
        dashboardAPI.getQuickWins(ORG_ID).catch(() => ({ quick_wins: [] })),
        dashboardAPI.getUtilizationReport(ORG_ID).catch(() => ({ summary: null })),
        dashboardAPI.getCategoryBreakdown(ORG_ID).catch(() => ({ categories: {} })),
        decisionsAPI.getPending(ORG_ID).catch(() => ({ total_pending: 0 })),
      ]);

      if (statsData) setStats(statsData);
      setQuickWins(quickWinsData.quick_wins || []);
      if (utilizationData.summary) setUtilization(utilizationData.summary);
      setCategorySpend(categoryData.categories || {});
      setPendingCount(pendingData.total_pending || 0);
    } catch (error) {
      console.error("Failed to load dashboard:", error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({
    title,
    value,
    subtitle,
    icon: Icon,
    trend,
    color = "blue",
  }: {
    title: string;
    value: string;
    subtitle?: string;
    icon: React.ElementType;
    trend?: string;
    color?: string;
  }) => (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-xl bg-${color}-50`}>
          <Icon className={`w-6 h-6 text-${color}-600`} />
        </div>
      </div>
      {trend && (
        <p className="text-sm text-green-600 mt-3 flex items-center gap-1">
          <TrendingDown className="w-4 h-4" />
          {trend}
        </p>
      )}
    </div>
  );

  if (loading) {
    return (
      <EnterpriseLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      </EnterpriseLayout>
    );
  }

  return (
    <EnterpriseLayout pendingDecisions={pendingCount}>
      <div className="space-y-6">
        {/* Demo Banner */}
        {USE_DEMO_DATA && (
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-purple-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">
                  Demo Mode - Explore Enterprise Features
                </h3>
                <p className="text-sm text-gray-600">
                  You&apos;re viewing a demo dashboard for Acme Corporation with sample data. 
                  Connect your organization to see real subscription data and AI-powered insights.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-500">Overview of your SaaS portfolio</p>
          </div>
          <Link
            href="/enterprise/decisions"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Zap className="w-4 h-4" />
            Run Analysis
          </Link>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Tools"
            value={stats?.total_tools?.toString() || "0"}
            subtitle={`${stats?.active_subscriptions || 0} with active subscriptions`}
            icon={Package}
            color="blue"
          />
          <StatCard
            title="Monthly Spend"
            value={formatCurrency(stats?.monthly_spend_cents || 0)}
            subtitle={`${formatCurrency(stats?.annual_spend_cents || 0)}/year`}
            icon={DollarSign}
            color="green"
          />
          <StatCard
            title="Potential Savings"
            value={formatCurrency(stats?.potential_savings_cents || 0)}
            subtitle={`${stats?.pending_decisions || 0} decisions pending`}
            icon={TrendingDown}
            color="amber"
          />
          <StatCard
            title="Avg Utilization"
            value={formatPercent(stats?.avg_utilization || 0)}
            subtitle={`${stats?.total_users || 0} total users`}
            icon={PieChart}
            color="purple"
          />
        </div>

        {/* Main content grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quick Wins */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Quick Wins</h2>
                  <p className="text-sm text-gray-500">Immediate optimization opportunities</p>
                </div>
                <span className="px-2.5 py-1 bg-amber-100 text-amber-700 text-sm font-medium rounded-full">
                  {quickWins.length} found
                </span>
              </div>
            </div>
            <div className="divide-y divide-gray-100">
              {quickWins.length === 0 ? (
                <div className="p-8 text-center">
                  <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                  <p className="text-gray-600">No quick wins found. Your portfolio looks healthy!</p>
                </div>
              ) : (
                quickWins.slice(0, 5).map((win, i) => (
                  <div key={i} className="p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start gap-4">
                      <div
                        className={`p-2 rounded-lg ${
                          win.priority === "high"
                            ? "bg-red-100 text-red-600"
                            : win.priority === "medium"
                            ? "bg-amber-100 text-amber-600"
                            : "bg-blue-100 text-blue-600"
                        }`}
                      >
                        {win.type === "zero_usage" ? (
                          <AlertTriangle className="w-5 h-5" />
                        ) : win.type === "departed_owner" ? (
                          <Users className="w-5 h-5" />
                        ) : (
                          <Package className="w-5 h-5" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900">
                          {win.tool_name || win.type.replace(/_/g, " ")}
                        </p>
                        <p className="text-sm text-gray-500">{win.action}</p>
                        {win.potential_annual_savings_cents && (
                          <p className="text-sm text-green-600 font-medium mt-1">
                            Save {formatCurrency(win.potential_annual_savings_cents)}/year
                          </p>
                        )}
                      </div>
                      <Link
                        href={`/enterprise/subscriptions/${win.subscription_id || ""}`}
                        className="p-2 rounded-lg hover:bg-gray-100 text-gray-400"
                      >
                        <ArrowRight className="w-5 h-5" />
                      </Link>
                    </div>
                  </div>
                ))
              )}
            </div>
            {quickWins.length > 5 && (
              <div className="p-4 border-t border-gray-200">
                <Link
                  href="/enterprise/decisions"
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  View all {quickWins.length} opportunities →
                </Link>
              </div>
            )}
          </div>

          {/* Utilization Summary */}
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Utilization Health</h2>
              <p className="text-sm text-gray-500">License usage across tools</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-sm text-gray-600">Healthy (&gt;70%)</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {utilization?.healthy_count || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-amber-500" />
                  <span className="text-sm text-gray-600">Moderate (50-70%)</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {utilization?.moderate_count || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orange-500" />
                  <span className="text-sm text-gray-600">Underutilized (30-50%)</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {utilization?.underutilized_count || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-sm text-gray-600">Critical (&lt;30%)</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {utilization?.critical_count || 0}
                </span>
              </div>

              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-500">Monthly waste</span>
                  <span className="text-sm font-bold text-red-600">
                    {formatCurrency(utilization?.total_monthly_waste_cents || 0)}
                  </span>
                </div>
                <Link
                  href="/enterprise/subscriptions"
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  View details →
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* Spend by Category */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Spend by Category</h2>
            <p className="text-sm text-gray-500">Monthly cost breakdown</p>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Object.entries(categorySpend).map(([category, data]) => (
                <div
                  key={category}
                  className="p-4 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                    {category.replace(/_/g, " ")}
                  </p>
                  <p className="text-lg font-bold text-gray-900">
                    {formatCurrency(data.monthly_spend_cents)}
                  </p>
                  <p className="text-xs text-gray-500">{data.tool_count} tools</p>
                </div>
              ))}
              {Object.keys(categorySpend).length === 0 && (
                <p className="col-span-full text-center text-gray-500 py-4">
                  No spend data available
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Pending Decisions CTA */}
        {pendingCount > 0 && (
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">
                  You have {pendingCount} decisions pending review
                </h3>
                <p className="text-blue-100 mt-1">
                  Review and approve recommendations to start saving
                </p>
              </div>
              <Link
                href="/enterprise/decisions"
                className="px-4 py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors"
              >
                Review Decisions
              </Link>
            </div>
          </div>
        )}
      </div>
    </EnterpriseLayout>
  );
}
