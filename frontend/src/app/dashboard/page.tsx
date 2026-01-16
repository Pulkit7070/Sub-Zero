"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw,
  Sparkles,
  DollarSign,
  TrendingDown,
  CreditCard,
  CheckCircle2,
} from "lucide-react";
import Layout from "@/components/Layout";
import ActionCard from "@/components/ActionCard";
import {
  api,
  Decision,
  DecisionStats,
  User,
  formatCurrency,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [stats, setStats] = useState<DecisionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [userData, decisionsData, statsData] = await Promise.all([
        api.getCurrentUser(),
        api.getDecisions(true),
        api.getDecisionStats(),
      ]);

      setUser(userData);
      setDecisions(decisionsData);
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load data:", err);
      if ((err as any).status === 401) {
        router.push("/");
        return;
      }
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      setError(null);
      const result = await api.syncSubscriptions();
      alert(
        `Sync complete! Found ${result.subscriptions_found} subscriptions (${result.new_subscriptions} new, ${result.updated_subscriptions} updated)`
      );
      await loadData();
    } catch (err) {
      console.error("Sync failed:", err);
      setError("Failed to sync subscriptions. Please try again.");
    } finally {
      setSyncing(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const result = await api.generateDecisions();
      alert(result.message);
      await loadData();
    } catch (err) {
      console.error("Generate failed:", err);
      setError("Failed to generate recommendations. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleAction = async (
    decisionId: string,
    action: "accepted" | "rejected" | "snoozed"
  ) => {
    await api.actOnDecision(decisionId, action);
    setDecisions((prev) => prev.filter((d) => d.id !== decisionId));
    // Reload stats
    const newStats = await api.getDecisionStats();
    setStats(newStats);
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">
            Welcome back{user?.email ? `, ${user.email.split("@")[0]}` : ""}!
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-secondary inline-flex items-center gap-2"
          >
            <RefreshCw
              className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`}
            />
            {syncing ? "Syncing..." : "Sync Gmail"}
          </button>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            {generating ? "Analyzing..." : "Get Recommendations"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Pending Actions</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats?.pending_decisions || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Actions Taken</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats?.accepted_decisions || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <TrendingDown className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Potential Savings</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(stats?.potential_savings_cents || 0)}
                <span className="text-sm text-gray-500 font-normal">/mo</span>
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Actual Savings</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(stats?.actual_savings_cents || 0)}
                <span className="text-sm text-gray-500 font-normal">/mo</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Feed */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Recommended Actions
        </h2>

        {decisions.length === 0 ? (
          <div className="card text-center py-12">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              All caught up!
            </h3>
            <p className="text-gray-600 mb-4">
              No pending recommendations. Sync your Gmail or generate new
              recommendations to get started.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={handleSync}
                disabled={syncing}
                className="btn-secondary inline-flex items-center gap-2"
              >
                <RefreshCw
                  className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`}
                />
                Sync Gmail
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="btn-primary inline-flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                Get Recommendations
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {decisions.map((decision) => (
              <ActionCard
                key={decision.id}
                decision={decision}
                onAction={(action) => handleAction(decision.id, action)}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
