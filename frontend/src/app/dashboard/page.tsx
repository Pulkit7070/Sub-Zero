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
  Flame,
  AlertTriangle,
  Clock,
  TrendingUp,
  Layers,
  X,
} from "lucide-react";
import Layout from "@/components/Layout";
import ActionCard from "@/components/ActionCard";
import {
  api,
  Decision,
  DecisionStats,
  User,
  IntelligenceStats,
  formatCurrency,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [stats, setStats] = useState<DecisionStats | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceStats | null>(null);
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

      const [userData, decisionsData, statsData, intelligenceData] = await Promise.all([
        api.getCurrentUser(),
        api.getDecisions(true),
        api.getDecisionStats(),
        api.getIntelligenceStats().catch(() => null),
      ]);

      setUser(userData);
      setDecisions(decisionsData);
      setStats(statsData);
      setIntelligence(intelligenceData);
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


  // Demo data for hackathon presentation (shown when no real data)
  const demoWasteStats = {
    annual_total_cents: 1428000,
    monthly_avg_cents: 119000,
    waste_score: 62,
    potentially_wasted_cents: 856800,
    equivalents: [
      { label: "months of groceries", value: 1.1, emoji: "🛒" },
      { label: "movie tickets", value: 17, emoji: "🎬" },
    ],
    shock_stat: "That's 1.1 months of groceries just... gone.",
  };

  const demoTrialAlerts = [
    { subscription_id: "1", vendor_name: "Netflix", trial_started_at: "2026-01-10", days_remaining: 2, is_urgent: true, estimated_charge_cents: 64900 },
    { subscription_id: "2", vendor_name: "Spotify", trial_started_at: "2026-01-05", days_remaining: 5, is_urgent: false, estimated_charge_cents: 11900 },
  ];

  const demoPriceChanges = [
    { subscription_id: "3", vendor_name: "Adobe Creative Cloud", old_amount_cents: 489900, new_amount_cents: 577500, change_percent: 17.9, detected_at: "2026-01-17" },
  ];

  const demoOverlaps = [
    { category: "Streaming Services", subscriptions: [{ id: "4", vendor_name: "Netflix", amount_cents: 64900, billing_cycle: "monthly" }, { id: "5", vendor_name: "Prime Video", amount_cents: 29900, billing_cycle: "monthly" }, { id: "6", vendor_name: "Hotstar", amount_cents: 29900, billing_cycle: "monthly" }], combined_monthly_cents: 124700, potential_savings_cents: 59800 },
  ];

  const demoNonUsePredictions = [
    { subscription_id: "7", vendor_name: "LinkedIn Premium", probability: 83, risk_level: "high" as const, reason: "No activity in 67 days", days_inactive: 67, amount_cents: 239900 },
    { subscription_id: "8", vendor_name: "Audible", probability: 65, risk_level: "medium" as const, reason: "Inactive for 45 days", days_inactive: 45, amount_cents: 19900 },
  ];

  // Use real data if available, otherwise use demo data
  const hasRealData = intelligence && (
    (intelligence.trial_alerts?.length || 0) > 0 ||
    (intelligence.price_changes?.length || 0) > 0 ||
    (intelligence.overlaps?.length || 0) > 0 ||
    (intelligence.non_use_predictions?.length || 0) > 0
  );

  const wasteStats = intelligence?.waste_stats || demoWasteStats;
  const trialAlerts = hasRealData ? (intelligence?.trial_alerts || []) : demoTrialAlerts;
  const priceChanges = hasRealData ? (intelligence?.price_changes || []) : demoPriceChanges;
  const overlaps = hasRealData ? (intelligence?.overlaps || []) : demoOverlaps;
  const nonUsePredictions = hasRealData ? (intelligence?.non_use_predictions || []) : demoNonUsePredictions;


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

      {/* Shock Stats - Emotional UI */}
      {wasteStats.potentially_wasted_cents > 0 && (
        <div className="glass-card border-red-500/20 mb-8 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-red-500/5 via-orange-500/5 to-red-500/5 animate-pulse"></div>
          
          <div className="relative z-10">
            <div className="flex items-start gap-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500/30 to-orange-500/20 flex items-center justify-center flex-shrink-0">
                <Flame className="w-8 h-8 text-red-400 animate-pulse" />
              </div>
              
              <div className="flex-1">
                <p className="text-slate-400 text-sm mb-1">You're burning money on unused subscriptions</p>
                <p className="text-4xl font-bold text-white mb-2">
                  {formatCurrency(wasteStats.potentially_wasted_cents, "INR")}
                  <span className="text-lg text-slate-500 font-normal">/year</span>
                </p>
                <p className="text-lg text-red-400 font-medium mb-4">
                  {wasteStats.shock_stat}
                </p>
                
                {wasteStats.equivalents.length > 0 && (
                  <div className="flex flex-wrap gap-3">
                    {wasteStats.equivalents.map((eq, i) => (
                      <div key={i} className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm">
                        <span className="mr-1">{eq.emoji}</span>
                        <span className="text-white font-medium">{eq.value}</span>
                        <span className="text-slate-400 ml-1">{eq.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="text-center">
                <div className="relative w-24 h-24">
                  <svg className="w-24 h-24 transform -rotate-90">
                    <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="none" className="text-slate-700" />
                    <circle cx="48" cy="48" r="40" stroke="url(#waste-gradient)" strokeWidth="8" fill="none" strokeDasharray={`${(100 - wasteStats.waste_score) * 2.51} 251`} className="transition-all duration-1000" />
                    <defs>
                      <linearGradient id="waste-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#ef4444" />
                        <stop offset="100%" stopColor="#f97316" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold text-white">{wasteStats.waste_score}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-400 mt-2">Health Score</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Intelligence Alerts Grid */}
      {(trialAlerts.length > 0 || priceChanges.length > 0 || overlaps.length > 0 || nonUsePredictions.length > 0) && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* Trial Alerts */}
          {trialAlerts.length > 0 && (
            <div className="glass-card border-amber-500/30">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Trial Ending</p>
                  <p className="text-xs text-slate-400">{trialAlerts.length} trial(s) expiring</p>
                </div>
              </div>
              {trialAlerts.slice(0, 2).map((trial) => (
                <div key={trial.subscription_id} className={`p-3 rounded-lg mb-2 ${trial.is_urgent ? 'bg-red-500/10 border border-red-500/30' : 'bg-white/5'}`}>
                  <div className="flex justify-between items-center">
                    <span className="text-white font-medium">{trial.vendor_name}</span>
                    <span className={`text-sm font-bold ${trial.is_urgent ? 'text-red-400' : 'text-amber-400'}`}>
                      {trial.days_remaining}d left
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Will charge {formatCurrency(trial.estimated_charge_cents, "INR")}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Price Hikes */}
          {priceChanges.length > 0 && (
            <div className="glass-card border-red-500/30">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-red-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Price Hikes</p>
                  <p className="text-xs text-slate-400">{priceChanges.length} increase(s) detected</p>
                </div>
              </div>
              {priceChanges.slice(0, 2).map((change) => (
                <div key={change.subscription_id} className="p-3 rounded-lg mb-2 bg-red-500/10 border border-red-500/20">
                  <div className="flex justify-between items-center">
                    <span className="text-white font-medium">{change.vendor_name}</span>
                    <span className="text-red-400 font-bold">+{change.change_percent}%</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {formatCurrency(change.old_amount_cents, "INR")} → {formatCurrency(change.new_amount_cents, "INR")}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Overlaps */}
          {overlaps.length > 0 && (
            <div className="glass-card border-indigo-500/30">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center">
                  <Layers className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Overlapping Tools</p>
                  <p className="text-xs text-slate-400">{overlaps.length} category(s) found</p>
                </div>
              </div>
              {overlaps.slice(0, 2).map((overlap, i) => (
                <div key={i} className="p-3 rounded-lg mb-2 bg-indigo-500/10 border border-indigo-500/20">
                  <div className="flex justify-between items-center">
                    <span className="text-white font-medium">{overlap.category}</span>
                    <span className="text-indigo-400 font-bold">{overlap.subscriptions.length} tools</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Save {formatCurrency(overlap.potential_savings_cents, "INR")}/mo
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Non-Use Predictions */}
          {nonUsePredictions.length > 0 && (
            <div className="glass-card border-purple-500/30">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Likely Unused</p>
                  <p className="text-xs text-slate-400">{nonUsePredictions.length} at risk</p>
                </div>
              </div>
              {nonUsePredictions.slice(0, 2).map((pred) => (
                <div key={pred.subscription_id} className="p-3 rounded-lg mb-2 bg-purple-500/10 border border-purple-500/20">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-white font-medium">{pred.vendor_name}</span>
                    <span className={`text-sm font-bold ${pred.risk_level === 'high' ? 'text-red-400' : pred.risk_level === 'medium' ? 'text-amber-400' : 'text-purple-400'}`}>
                      {pred.probability}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-1.5 mb-2">
                    <div 
                      className={`h-1.5 rounded-full ${pred.risk_level === 'high' ? 'bg-red-500' : pred.risk_level === 'medium' ? 'bg-amber-500' : 'bg-purple-500'}`}
                      style={{ width: `${pred.probability}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-400">{pred.reason}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="gradient-card group hover:scale-[1.02] transition-transform duration-300">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-sky-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <CreditCard className="w-6 h-6 text-sky-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Pending Actions</p>
              <p className="text-2xl font-bold text-white">{stats?.pending_decisions || 0}</p>
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
              <p className="text-2xl font-bold text-white">{stats?.accepted_decisions || 0}</p>
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
            <h3 className="text-xl font-semibold text-white mb-2">All caught up!</h3>
            <p className="text-slate-400 mb-6 max-w-md mx-auto">
              No pending recommendations. Sync your Gmail or generate new recommendations to get started.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button onClick={handleSync} disabled={syncing} className="btn-secondary inline-flex items-center gap-2">
                <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
                Sync Gmail
              </button>
              <button onClick={handleGenerate} disabled={generating} className="btn-primary inline-flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Get Recommendations
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {decisions.map((decision) => (
              <ActionCard key={decision.id} decision={decision} onAction={(action) => handleAction(decision.id, action)} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
