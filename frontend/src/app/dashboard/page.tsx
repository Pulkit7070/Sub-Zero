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
  Zap,
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
    const newStats = await api.getDecisionStats();
    setStats(newStats);
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 rounded-full border-2 border-sky-500/30 border-t-sky-500 animate-spin"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-slate-400">
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
        <div className="glass-card border-red-500/30 bg-red-500/10 text-red-400 px-4 py-3 mb-6">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="gradient-card group hover:scale-[1.02] transition-transform duration-300">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-sky-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <CreditCard className="w-6 h-6 text-sky-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Pending Actions</p>
              <p className="text-2xl font-bold text-white">
                {stats?.pending_decisions || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="gradient-card group hover:scale-[1.02] transition-transform duration-300">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Actions Taken</p>
              <p className="text-2xl font-bold text-white">
                {stats?.accepted_decisions || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="gradient-card group hover:scale-[1.02] transition-transform duration-300">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <TrendingDown className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Potential Savings</p>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(stats?.potential_savings_cents || 0)}
                <span className="text-sm text-slate-500 font-normal">/mo</span>
              </p>
            </div>
          </div>
        </div>

        <div className="gradient-card group hover:scale-[1.02] transition-transform duration-300">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <DollarSign className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Actual Savings</p>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(stats?.actual_savings_cents || 0)}
                <span className="text-sm text-slate-500 font-normal">/mo</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Feed */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-400" />
          Recommended Actions
        </h2>

        {decisions.length === 0 ? (
          <div className="glass-card text-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-5">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              All caught up!
            </h3>
            <p className="text-slate-400 mb-6 max-w-md mx-auto">
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
